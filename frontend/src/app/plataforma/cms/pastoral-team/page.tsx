"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import {
  Heart,
  Instagram,
  Facebook,
  Twitter,
  Search,
  UserPlus,
  X,
  Check,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Pencil,
  ImageIcon,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import {
  PastoralProfile,
  getCmsPastoralTeam,
  updateCmsPastoralProfile,
} from "@/lib/cms/v2";
import ViewSwitcher, { ViewType } from "@/components/ViewSwitcher";
import MediaPicker from "@/components/cms/builder/MediaPicker";

interface PersonaSearchResult {
  id: string;
  nombre_completo?: string;
  name?: string;
  church_role?: string;
  is_pastoral_leader?: boolean;
}

type DrawerMode = "edit" | "add" | null;

export default function PastoralTeamPage() {
  const { token } = useAuth();
  const [profiles, setProfiles] = useState<PastoralProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [viewType, setViewType] = useState<ViewType>("grid");
  const [drawerMode, setDrawerMode] = useState<DrawerMode>(null);
  const [editing, setEditing] = useState<PastoralProfile | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [addSearch, setAddSearch] = useState("");
  const [addResults, setAddResults] = useState<PersonaSearchResult[]>([]);
  const [searchingAdd, setSearchingAdd] = useState(false);
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);

  const PER_PAGE = 12;

  const fetchProfiles = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await getCmsPastoralTeam(token);
      setProfiles(data);
    } catch {
      setError("Error al cargar los perfiles pastorales");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchProfiles();
  }, [fetchProfiles]);

  const filtered = useMemo(() => {
    if (!search.trim()) return profiles;
    const q = search.toLowerCase();
    return profiles.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.role && p.role.toLowerCase().includes(q))
    );
  }, [profiles, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE));
  const paginated = filtered.slice(page * PER_PAGE, (page + 1) * PER_PAGE);

  const openDrawer = (profile: PastoralProfile) => {
    setEditing(profile);
    setDrawerMode("edit");
    setError(null);
    setSuccessMsg(null);
  };

  const closeDrawer = () => {
    setDrawerMode(null);
    setEditing(null);
    setError(null);
    setSuccessMsg(null);
    setAddSearch("");
    setAddResults([]);
  };

  const handleSave = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editing || !token) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    const formData = new FormData(e.currentTarget);
    const bioShort = formData.get("bio_short") as string;
    const bioFull = formData.get("bio_full") as string;
    const socialInstagram = formData.get("social_instagram") as string;
    const socialFacebook = formData.get("social_facebook") as string;
    const socialTwitter = formData.get("social_twitter") as string;
    const isMainPastor = formData.get("is_main_pastor") === "on";
    const isPastoralPublished = formData.get("is_pastoral_published") === "on";
    const pastoralSortOrder = parseInt(formData.get("pastoral_sort_order") as string) || 0;

    const data: Record<string, string | number | boolean | null> = {};

    // Always send photo_url from editing state (MediaPicker updates it directly)
    if (editing.photo_url) data.photo_url = editing.photo_url;
    if (bioShort !== (editing.bio_short || ""))
      data.bio_short = bioShort || null;
    if (bioFull !== (editing.bio_full || "")) data.bio_full = bioFull || null;
    if (socialInstagram !== (editing.social_instagram || ""))
      data.social_instagram = socialInstagram || null;
    if (socialFacebook !== (editing.social_facebook || ""))
      data.social_facebook = socialFacebook || null;
    if (socialTwitter !== (editing.social_twitter || ""))
      data.social_twitter = socialTwitter || null;
    if (isMainPastor !== editing.is_main_pastor)
      data.is_main_pastor = isMainPastor;
    if (isPastoralPublished !== (editing.is_pastoral_published !== false))
      data.is_pastoral_published = isPastoralPublished;
    if (pastoralSortOrder !== (editing.pastoral_sort_order || 0))
      data.pastoral_sort_order = pastoralSortOrder;

    if (Object.keys(data).length === 0) {
      closeDrawer();
      return;
    }

    try {
      await updateCmsPastoralProfile(editing.id, data, token);
      setSuccessMsg("Perfil actualizado correctamente");
      fetchProfiles();
      setTimeout(closeDrawer, 1200);
    } catch {
      setError("Error al guardar los cambios");
    } finally {
      setSaving(false);
    }
  };

  const handleAddLeader = async (personaId: string) => {
    if (!token) return;
    setSaving(true);
    try {
      await updateCmsPastoralProfile(
        personaId,
        { is_pastoral_leader: true } as Partial<PastoralProfile>,
        token
      );
      setSuccessMsg("Líder agregado al equipo pastoral");
      fetchProfiles();
      setAddSearch("");
      setAddResults([]);
      setDrawerMode(null);
    } catch {
      setError("Error al agregar líder");
    } finally {
      setSaving(false);
    }
  };

  const searchPersonas = async (q: string) => {
    setAddSearch(q);
    if (q.trim().length < 3) {
      setAddResults([]);
      return;
    }
    setSearchingAdd(true);
    try {
      const res = await apiFetch<PersonaSearchResult[]>(
        `/crm/v2/personas?q=${encodeURIComponent(q)}&limit=10`,
        { token }
      );
      const existingIds = new Set(profiles.map((p) => p.id));
      setAddResults(
        (res || []).filter(
          (p: PersonaSearchResult) => !existingIds.has(p.id) && !p.is_pastoral_leader
        )
      );
    } catch {
      setAddResults([]);
    } finally {
      setSearchingAdd(false);
    }
  };

  return (
    <div className="min-h-screen bg-[hsl(var(--bg-primary))] dark:bg-[var(--bg-primary)]">
      {/* ── Actions Bar ── */}
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12 py-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="relative flex-1 max-w-sm">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
              placeholder="Buscar por nombre..."
              className="w-full pl-9 pr-4 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[hsl(var(--text-secondary))]">
              {filtered.length} líderes
            </span>
            <ViewSwitcher
              viewType={viewType}
              setViewType={setViewType}
              availableViews={["grid", "list", "table"]}
              storageKey="pastoral-team-view"
            />
            <button
              onClick={() => setDrawerMode("add")}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wider hover:opacity-90 transition-all"
            >
              <UserPlus size={14} />
              Agregar líder
            </button>
          </div>
        </div>
      </div>

      {/* ── Grid / Loading ── */}
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12 pb-20">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 rounded-full border-2 border-[hsl(var(--primary))] border-t-transparent animate-spin" />
          </div>
        ) : paginated.length === 0 ? (
          <div className="text-center py-20">
            <Heart
              size={40}
              className="mx-auto text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mb-4"
            />
            <p className="text-[hsl(var(--text-secondary))]">
              {search
                ? "No se encontraron líderes con ese nombre."
                : "No hay líderes pastorales registrados. ¡Agrega el primero!"}
            </p>
          </div>
        ) : (
          <>
            {/* Grid View */}
            {viewType === "grid" && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {paginated.map((profile) => (
                  <div
                    key={profile.id}
                    className="group relative bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-deep))] rounded-xl border border-[hsl(var(--border))]/70 dark:border-white/[0.06] p-4 flex items-start gap-4 hover:shadow-lg hover:-translate-y-0.5 transition-all"
                  >
                    <div className="relative w-14 h-14 rounded-full overflow-hidden bg-[hsl(var(--surface-2))] dark:bg-[hsl(var(--surface-2))] shrink-0 ring-2 ring-[hsl(var(--border))]/50 dark:ring-white/[0.06]">
                      {profile.photo_url ? (
                        <Image src={profile.photo_url} alt={profile.name} fill className="object-cover" sizes="56px" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[hsl(var(--primary))/0.1] to-[hsl(var(--secondary))/0.05]">
                          <span className="text-lg font-bold text-[hsl(var(--primary))/0.3]">{profile.name.charAt(0)}</span>
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-sm text-[hsl(var(--text-primary))] dark:text-white truncate">{profile.name}</h3>
                        {profile.is_main_pastor && <Sparkles size={12} className="text-[hsl(var(--primary))] shrink-0" />}
                      </div>
                      <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">{profile.role || "Pastor"}</p>
                      <div className="flex items-center gap-2 mt-2">
                        {profile.social_instagram && <Instagram size={12} className="text-[hsl(var(--text-secondary))]" />}
                        {profile.social_facebook && <Facebook size={12} className="text-[hsl(var(--text-secondary))]" />}
                        {profile.social_twitter && <Twitter size={12} className="text-[hsl(var(--text-secondary))]" />}
                        {!profile.social_instagram && !profile.social_facebook && !profile.social_twitter && (
                          <span className="text-[9px] text-[hsl(var(--text-secondary))]">Sin redes</span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => openDrawer(profile)}
                      className="absolute top-3 right-3 w-7 h-7 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))/0.1] opacity-0 group-hover:opacity-100 transition-all"
                      aria-label="Editar"
                    >
                      <Pencil size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* List View */}
            {viewType === "list" && (
              <div className="space-y-2">
                {paginated.map((profile) => (
                  <div
                    key={profile.id}
                    className="group flex items-center gap-4 p-3 rounded-xl border border-[hsl(var(--border))]/70 dark:border-white/[0.06] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-deep))] hover:shadow-md transition-all cursor-pointer"
                    onClick={() => openDrawer(profile)}
                  >
                    <div className="relative w-10 h-10 rounded-full overflow-hidden bg-[hsl(var(--surface-2))] dark:bg-[hsl(var(--surface-2))] shrink-0">
                      {profile.photo_url ? (
                        <Image src={profile.photo_url} alt={profile.name} fill className="object-cover" sizes="40px" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[hsl(var(--primary))/0.1] to-[hsl(var(--secondary))/0.05]">
                          <span className="text-sm font-bold text-[hsl(var(--primary))/0.3]">{profile.name.charAt(0)}</span>
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">{profile.name}</p>
                        {profile.is_main_pastor && <Sparkles size={10} className="text-[hsl(var(--primary))]" />}
                      </div>
                      <p className="text-[11px] text-[hsl(var(--text-secondary))]">{profile.role || "Pastor"}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {profile.social_instagram && <Instagram size={12} className="text-[hsl(var(--text-secondary))]" />}
                      {profile.social_facebook && <Facebook size={12} className="text-[hsl(var(--text-secondary))]" />}
                      {profile.social_twitter && <Twitter size={12} className="text-[hsl(var(--text-secondary))]" />}
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); openDrawer(profile); }}
                      className="p-2 rounded-lg hover:bg-[hsl(var(--primary))/0.1] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"
                    >
                      <Pencil size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Table View */}
            {viewType === "table" && (
              <div className="overflow-x-auto rounded-xl border border-[hsl(var(--border))]/70 dark:border-white/[0.06]">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[hsl(var(--border))] dark:border-white/[0.06] bg-[hsl(var(--surface-1))] dark:bg-white/[0.02]">
                      <th className="text-left px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Foto</th>
                      <th className="text-left px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Nombre</th>
                      <th className="text-left px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Rol</th>
                      <th className="text-left px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Redes</th>
                      <th className="text-left px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Principal</th>
                      <th className="text-right px-4 py-3 text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginated.map((profile) => (
                      <tr key={profile.id} className="border-b border-[hsl(var(--border))]/50 dark:border-white/[0.03] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] transition-colors">
                        <td className="px-4 py-3">
                          <div className="relative w-8 h-8 rounded-full overflow-hidden bg-[hsl(var(--surface-2))] dark:bg-[hsl(var(--surface-2))]">
                            {profile.photo_url ? (
                              <Image src={profile.photo_url} alt={profile.name} fill className="object-cover" sizes="32px" />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[hsl(var(--primary))/0.1] to-[hsl(var(--secondary))/0.05]">
                                <span className="text-xs font-bold text-[hsl(var(--primary))/0.3]">{profile.name.charAt(0)}</span>
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-[hsl(var(--text-primary))] dark:text-white">{profile.name}</span>
                            {profile.is_main_pastor && <Sparkles size={10} className="text-[hsl(var(--primary))]" />}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-[hsl(var(--text-secondary))]">{profile.role || "Pastor"}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1">
                            {profile.social_instagram && <Instagram size={12} className="text-[hsl(var(--text-secondary))]" />}
                            {profile.social_facebook && <Facebook size={12} className="text-[hsl(var(--text-secondary))]" />}
                            {profile.social_twitter && <Twitter size={12} className="text-[hsl(var(--text-secondary))]" />}
                            {!profile.social_instagram && !profile.social_facebook && !profile.social_twitter && (
                              <span className="text-[10px] text-[hsl(var(--text-secondary))]">—</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {profile.is_main_pastor ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[hsl(var(--primary))/0.1 text-[hsl(var(--primary))] text-[10px] font-semibold">
                              <Check size={10} /> Sí
                            </span>
                          ) : (
                            <span className="text-[10px] text-[hsl(var(--text-secondary))]">No</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => openDrawer(profile)}
                            className="p-1.5 rounded-lg hover:bg-[hsl(var(--primary))/0.1 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"
                          >
                            <Pencil size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3 mt-8">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="w-9 h-9 rounded-xl bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] disabled:opacity-30 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/10 transition-all"
                >
                  <ChevronLeft size={16} />
                </button>
                <span className="text-xs font-bold text-[hsl(var(--text-secondary))]">
                  {page + 1} / {totalPages}
                </span>
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="w-9 h-9 rounded-xl bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] disabled:opacity-30 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/10 transition-all"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Edit Drawer ── */}
      {drawerMode === "edit" && editing && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={closeDrawer}
          />
          <div className="relative w-full max-w-2xl bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-l border-[hsl(var(--border))] dark:border-white/[0.06] shadow-2xl overflow-y-auto">
            <div className="sticky top-0 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-b border-[hsl(var(--border))] dark:border-white/[0.06] px-6 py-4 flex items-center justify-between z-10">
              <h2 className="text-sm font-bold uppercase tracking-wider">
                Editar perfil
              </h2>
              <button
                onClick={closeDrawer}
                className="w-8 h-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 transition-all"
              >
                <X size={14} />
              </button>
            </div>

            <form onSubmit={handleSave} className="p-6 space-y-5">
              {error && (
                <div className="p-3 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-xs text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))]">
                  {error}
                </div>
              )}
              {successMsg && (
                <div className="p-3 rounded-xl bg-success-soft dark:bg-[hsl(var(--success))]/10 border border-[hsl(var(--success)/25%)] dark:border-[hsl(var(--success)/100%)]/20 text-xs text-success-text dark:text-[hsl(var(--success))] flex items-center gap-2">
                  <Check size={14} />
                  {successMsg}
                </div>
              )}

              {/* Nombre (readonly) */}
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5">
                  Nombre
                </label>
                <p className="text-sm font-medium text-[hsl(var(--text-primary))] dark:text-white">
                  {editing.name}
                </p>
              </div>

              {/* Rol (readonly) */}
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5">
                  Rol
                </label>
                <p className="text-sm text-[hsl(var(--text-secondary))]">
                  {editing.role || "Pastor"}
                </p>
              </div>

              {/* Photo URL */}
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5">
                  Foto del perfil
                </label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <ImageIcon
                      size={14}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]"
                    />
                    <input
                      name="photo_url"
                      type="text"
                      value={editing.photo_url || ""}
                      onChange={(e) => setEditing({ ...editing, photo_url: e.target.value })}
                      placeholder="URL de la foto"
                      className="w-full pl-9 pr-4 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => setMediaPickerOpen(true)}
                    className="px-3 py-2 rounded-xl bg-[hsl(var(--primary))/0.1 text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))/0.2 transition-colors text-xs font-semibold"
                  >
                    <ImageIcon size={14} />
                  </button>
                </div>
                {editing.photo_url && (
                  <div className="mt-2 relative w-20 h-20 rounded-xl overflow-hidden border border-[hsl(var(--border))] dark:border-white/10">
                    <Image src={editing.photo_url} alt="Preview" fill className="object-cover" sizes="80px" />
                  </div>
                )}
              </div>

              {/* Bio short */}
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5">
                  Biografía corta
                </label>
                <textarea
                  name="bio_short"
                  defaultValue={editing.bio_short || ""}
                  rows={2}
                  placeholder="Breve descripción para la tarjeta..."
                  className="w-full px-4 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] resize-none"
                />
              </div>

              {/* Bio full */}
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5">
                  Historia completa (HTML)
                </label>
                <textarea
                  name="bio_full"
                  defaultValue={editing.bio_full || ""}
                  rows={4}
                  placeholder="Historia completa del pastor (soporta HTML)..."
                  className="w-full px-4 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] resize-none font-mono"
                />
              </div>

              {/* Social */}
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5 flex items-center gap-1.5">
                    <Instagram size={12} /> Instagram URL
                  </label>
                  <input
                    name="social_instagram"
                    type="url"
                    defaultValue={editing.social_instagram || ""}
                    placeholder="https://instagram.com/..."
                    className="w-full px-4 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5 flex items-center gap-1.5">
                    <Facebook size={12} /> Facebook URL
                  </label>
                  <input
                    name="social_facebook"
                    type="url"
                    defaultValue={editing.social_facebook || ""}
                    placeholder="https://facebook.com/..."
                    className="w-full px-4 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5 flex items-center gap-1.5">
                    <Twitter size={12} /> X (Twitter) URL
                  </label>
                  <input
                    name="social_twitter"
                    type="url"
                    defaultValue={editing.social_twitter || ""}
                    placeholder="https://x.com/..."
                    className="w-full px-4 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Toggle is_main_pastor */}
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  name="is_main_pastor"
                  type="checkbox"
                  defaultChecked={editing.is_main_pastor}
                  className="w-4 h-4 rounded border-[hsl(var(--border))] dark:border-white/20 text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))/0.3]"
                />
                <div>
                  <span className="text-sm font-medium text-[hsl(var(--text-primary))] dark:text-white">
                    Pastor Principal
                  </span>
                  <p className="text-[10px] text-[hsl(var(--text-secondary))]">
                    Aparece resaltado en la página pública
                  </p>
                </div>
              </label>

              {/* Toggle is_pastoral_published */}
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  name="is_pastoral_published"
                  type="checkbox"
                  defaultChecked={editing.is_pastoral_published !== false}
                  className="w-4 h-4 rounded border-[hsl(var(--border))] dark:border-white/20 text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))/0.3]"
                />
                <div>
                  <span className="text-sm font-medium text-[hsl(var(--text-primary))] dark:text-white">
                    Publicado
                  </span>
                  <p className="text-[10px] text-[hsl(var(--text-secondary))]">
                    Visible en el sitio público
                  </p>
                </div>
              </label>

              {/* Sort Order */}
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5">
                  Orden de aparición
                </label>
                <input
                  name="pastoral_sort_order"
                  type="number"
                  defaultValue={editing.pastoral_sort_order || 0}
                  min="0"
                  className="w-full px-4 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                />
                <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-1">
                  Menor número = aparece primero
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-3 pt-4 border-t border-[hsl(var(--border))] dark:border-white/[0.06]">
                <button
                  type="button"
                  onClick={closeDrawer}
                  className="flex-1 py-2.5 rounded-xl bg-[hsl(var(--surface-2))] dark:bg-white/5 text-sm font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 py-2.5 rounded-xl bg-[hsl(var(--primary))] text-white text-sm font-bold uppercase tracking-wider hover:opacity-90 disabled:opacity-50 transition-all"
                >
                  {saving ? "Guardando..." : "Guardar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Add Drawer ── */}
      {drawerMode === "add" && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={closeDrawer}
          />
          <div className="relative w-full max-w-lg bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-l border-[hsl(var(--border))] dark:border-white/[0.06] shadow-2xl overflow-y-auto">
            <div className="sticky top-0 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-b border-[hsl(var(--border))] dark:border-white/[0.06] px-6 py-4 flex items-center justify-between z-10">
              <h2 className="text-sm font-bold uppercase tracking-wider">
                Agregar líder pastoral
              </h2>
              <button
                onClick={closeDrawer}
                className="w-8 h-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 transition-all"
              >
                <X size={14} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {successMsg && (
                <div className="p-3 rounded-xl bg-success-soft dark:bg-[hsl(var(--success))]/10 border border-[hsl(var(--success)/25%)] dark:border-[hsl(var(--success)/100%)]/20 text-xs text-success-text dark:text-[hsl(var(--success))] flex items-center gap-2">
                  <Check size={14} />
                  {successMsg}
                </div>
              )}
              <p className="text-xs text-[hsl(var(--text-secondary))]">
                Busca una persona existente para agregarla como líder pastoral.
              </p>

              <div className="relative">
                <Search
                  size={16}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]"
                />
                <input
                  type="text"
                  value={addSearch}
                  onChange={(e) => searchPersonas(e.target.value)}
                  placeholder="Buscar por nombre (mín. 3 caracteres)..."
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                />
              </div>

              {searchingAdd && (
                <div className="flex items-center justify-center py-8">
                  <div className="w-6 h-6 rounded-full border-2 border-[hsl(var(--primary))] border-t-transparent animate-spin" />
                </div>
              )}

              {!searchingAdd && addSearch.length >= 3 && (
                <>
                  {addResults.length === 0 ? (
                    <p className="text-center py-8 text-xs text-[hsl(var(--text-secondary))]">
                      {addSearch.trim()
                        ? "No se encontraron personas disponibles."
                        : "Escribe para buscar..."}
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {addResults.map((persona: PersonaSearchResult) => (
                        <div
                          key={persona.id}
                          className="flex items-center justify-between p-3 rounded-xl bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] border border-[hsl(var(--border))] dark:border-white/[0.04]"
                        >
                          <div>
                            <p className="text-sm font-medium text-[hsl(var(--text-primary))] dark:text-white">
                              {persona.nombre_completo || persona.name}
                            </p>
                            <p className="text-[10px] text-[hsl(var(--text-secondary))]">
                              {persona.church_role || "Persona"}
                            </p>
                          </div>
                          <button
                            onClick={() => handleAddLeader(persona.id)}
                            disabled={saving}
                            className="px-3 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase tracking-wider hover:opacity-90 disabled:opacity-50 transition-all"
                          >
                            {saving ? "..." : "Agregar"}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}

              <div className="flex pt-2">
                <button
                  type="button"
                  onClick={closeDrawer}
                  className="flex-1 py-2.5 rounded-xl bg-[hsl(var(--surface-2))] dark:bg-white/5 text-sm font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 transition-all"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Media Picker */}
      {mediaPickerOpen && (
        <MediaPicker
          open
          token={token}
          selectedUrl={editing?.photo_url || undefined}
          onClose={() => setMediaPickerOpen(false)}
          onSelect={(item) => {
            const url = typeof item === "string" ? item : (item as { url?: string }).url || "";
            if (url && editing) {
              setEditing({ ...editing, photo_url: url });
            }
            setMediaPickerOpen(false);
          }}
        />
      )}
    </div>
  );
}

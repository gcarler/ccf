"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
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
  Trash2,
  ExternalLink,
  BookOpen,
  Quote,
  Loader2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import {
  PastoralProfile,
  getCmsPastoralTeam,
  updateCmsPastoralProfile,
  createCmsPastoralProfile,
  deleteCmsPastoralProfile,
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
type AddTab = "create" | "link";

interface NewPastorState {
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

const defaultNewPastor: NewPastorState = {
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

export default function PastoralTeamPage() {
  const { token } = useAuth();
  const [profiles, setProfiles] = useState<PastoralProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [viewType, setViewType] = useState<ViewType>("grid");
  const [drawerMode, setDrawerMode] = useState<DrawerMode>(null);
  const [editing, setEditing] = useState<PastoralProfile | null>(null);
  const [newPastor, setNewPastor] = useState<NewPastorState>(defaultNewPastor);
  const [addTab, setAddTab] = useState<AddTab>("create");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [addSearch, setAddSearch] = useState("");
  const [addResults, setAddResults] = useState<PersonaSearchResult[]>([]);
  const [searchingAdd, setSearchingAdd] = useState(false);
  const [mediaPickerOpen, setMediaPickerOpen] = useState(false);
  const [mediaPickerTarget, setMediaPickerTarget] = useState<"edit" | "create">("edit");
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const PER_PAGE = 12;

  const fetchProfiles = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await getCmsPastoralTeam(token);
      setProfiles(Array.isArray(data) ? data : []);
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
    setEditing({ ...profile });
    setDrawerMode("edit");
    setError(null);
    setSuccessMsg(null);
    setConfirmDeleteId(null);
  };

  const openAddDrawer = () => {
    setNewPastor({
      ...defaultNewPastor,
      pastoral_sort_order: profiles.length * 10,
    });
    setAddTab("create");
    setDrawerMode("add");
    setError(null);
    setSuccessMsg(null);
    setConfirmDeleteId(null);
  };

  const closeDrawer = () => {
    setDrawerMode(null);
    setEditing(null);
    setNewPastor(defaultNewPastor);
    setError(null);
    setSuccessMsg(null);
    setAddSearch("");
    setAddResults([]);
    setConfirmDeleteId(null);
  };

  const handleSave = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editing || !token) return;
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    const formData = new FormData(e.currentTarget);
    const name = (formData.get("name") as string)?.trim();
    const role = (formData.get("role") as string)?.trim();
    const photoUrl = editing.photo_url || "";
    const bioShort = formData.get("bio_short") as string;
    const bioFull = formData.get("bio_full") as string;
    const socialInstagram = formData.get("social_instagram") as string;
    const socialFacebook = formData.get("social_facebook") as string;
    const socialTwitter = formData.get("social_twitter") as string;
    const isMainPastor = formData.get("is_main_pastor") === "on";
    const isPastoralPublished = formData.get("is_pastoral_published") === "on";
    const pastoralSortOrder = parseInt(formData.get("pastoral_sort_order") as string) || 0;

    const data: Record<string, string | number | boolean | null> = {};

    if (name && name !== editing.name) data.name = name;
    if (role && role !== (editing.role || "")) {
      data.role = role;
      data.church_role = role;
    }
    data.photo_url = photoUrl || null;
    data.bio_short = bioShort || null;
    data.bio_full = bioFull || null;
    data.social_instagram = socialInstagram || null;
    data.social_facebook = socialFacebook || null;
    data.social_twitter = socialTwitter || null;
    data.is_main_pastor = isMainPastor;
    data.is_pastoral_published = isPastoralPublished;
    data.pastoral_sort_order = pastoralSortOrder;

    try {
      await updateCmsPastoralProfile(editing.id, data, token);
      setSuccessMsg("Perfil pastoral e historia actualizados");
      fetchProfiles();
      setTimeout(closeDrawer, 1200);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al guardar los cambios");
    } finally {
      setSaving(false);
    }
  };

  const handleCreatePastor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    if (!newPastor.name.trim()) {
      setError("El nombre del pastor es requerido");
      return;
    }
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    try {
      await createCmsPastoralProfile(
        {
          name: newPastor.name.trim(),
          church_role: newPastor.role.trim() || "Pastor",
          role: newPastor.role.trim() || "Pastor",
          photo_url: newPastor.photo_url.trim() || null,
          bio_short: newPastor.bio_short.trim() || null,
          bio_full: newPastor.bio_full.trim() || null,
          social_instagram: newPastor.social_instagram.trim() || null,
          social_facebook: newPastor.social_facebook.trim() || null,
          social_twitter: newPastor.social_twitter.trim() || null,
          is_main_pastor: newPastor.is_main_pastor,
          is_pastoral_published: newPastor.is_pastoral_published,
          pastoral_sort_order: Number(newPastor.pastoral_sort_order) || 0,
        },
        token
      );
      setSuccessMsg("Nuevo pastor creado correctamente");
      fetchProfiles();
      setTimeout(closeDrawer, 1200);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al crear el nuevo pastor");
    } finally {
      setSaving(false);
    }
  };

  const handleDeletePastor = async (personaId: string) => {
    if (!token) return;
    setSaving(true);
    setError(null);
    try {
      await deleteCmsPastoralProfile(personaId, token);
      setSuccessMsg("Pastor removido del equipo pastoral");
      fetchProfiles();
      setTimeout(closeDrawer, 1000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error al remover el pastor");
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
        { is_pastoral_leader: true, is_pastoral_published: true } as Partial<PastoralProfile>,
        token
      );
      setSuccessMsg("Líder agregado al equipo pastoral");
      fetchProfiles();
      setAddSearch("");
      setAddResults([]);
      setTimeout(closeDrawer, 1000);
    } catch {
      setError("Error al vincular líder");
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
      <div className="px-4 md:px-6 lg:px-8 xl:px-12 py-6">
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
              placeholder="Buscar por nombre o rol..."
              className="w-full pl-9 pr-4 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-[hsl(var(--text-secondary))] font-medium">
              {filtered.length} líderes
            </span>
            <ViewSwitcher
              viewType={viewType}
              setViewType={setViewType}
              availableViews={["grid", "list", "table"]}
              storageKey="pastoral-team-view"
            />
            <button
              onClick={openAddDrawer}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wider hover:opacity-90 transition-all shadow-md shadow-[hsl(var(--primary))/0.2]"
            >
              <UserPlus size={14} />
              Agregar pastor
            </button>
          </div>
        </div>
      </div>

      {/* ── Grid / Loading ── */}
      <div className="px-4 md:px-6 lg:px-8 xl:px-12 pb-20">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 rounded-full border-2 border-[hsl(var(--primary))] border-t-transparent animate-spin" />
          </div>
        ) : paginated.length === 0 ? (
          <div className="text-center py-20">
            <Heart
              size={40}
              className="mx-auto text-[hsl(var(--text-secondary))] mb-4 opacity-40"
            />
            <p className="text-[hsl(var(--text-secondary))]">
              {search
                ? "No se encontraron líderes con ese nombre o rol."
                : "No hay líderes pastorales registrados. ¡Crea el primero!"}
            </p>
            {!search && (
              <button
                onClick={openAddDrawer}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wider hover:opacity-90 transition-all"
              >
                <UserPlus size={14} />
                Crear Nuevo Pastor
              </button>
            )}
          </div>
        ) : (
          <>
            {/* Grid View */}
            {viewType === "grid" && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {paginated.map((profile) => (
                  <div
                    key={profile.id}
                    className="group relative bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-deep))] rounded-2xl border border-[hsl(var(--border))]/70 dark:border-white/[0.06] p-4 flex flex-col justify-between hover:shadow-xl hover:border-[hsl(var(--primary))/0.4] transition-all"
                  >
                    <div>
                      <div className="flex items-start gap-3">
                        <div className="relative w-14 h-14 rounded-xl overflow-hidden bg-[hsl(var(--surface-2))] shrink-0 ring-2 ring-[hsl(var(--border))]/50 dark:ring-white/[0.06]">
                          {profile.photo_url ? (
                            <Image
                              src={profile.photo_url}
                              alt={profile.name}
                              fill
                              className="object-cover"
                              sizes="56px"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-[hsl(var(--primary))/0.1] to-[hsl(var(--secondary))/0.05]">
                              <span className="text-lg font-bold text-[hsl(var(--primary))/0.5]">
                                {profile.name.charAt(0)}
                              </span>
                            </div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <h3 className="font-semibold text-sm text-[hsl(var(--text-primary))] dark:text-white truncate">
                              {profile.name}
                            </h3>
                            {profile.is_main_pastor && (
                              <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-[hsl(var(--primary))/0.15] text-[hsl(var(--primary))] text-3xs font-bold uppercase">
                                <Sparkles size={9} /> Principal
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5 font-medium">
                            {profile.role || "Pastor"}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            {profile.is_pastoral_published !== false ? (
                              <span className="inline-flex items-center gap-1 text-3xs text-[hsl(var(--success))] font-semibold">
                                <span className="w-1.5 h-1.5 rounded-full bg-[hsl(var(--success))]" /> Publicado
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-3xs text-[hsl(var(--text-secondary))] font-semibold">
                                <span className="w-1.5 h-1.5 rounded-full bg-neutral-400" /> Oculto
                              </span>
                            )}
                            <span className="text-3xs text-[hsl(var(--text-secondary))] font-mono">
                              #{profile.pastoral_sort_order ?? 0}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Excerpt / Story preview */}
                      <div className="mt-3 pt-2.5 border-t border-[hsl(var(--border))]/60 dark:border-white/5 space-y-1.5">
                        {profile.bio_short ? (
                          <p className="text-xs text-[hsl(var(--text-secondary))] line-clamp-2 italic">
                            &ldquo;{profile.bio_short.replace(/<[^>]*>/g, "")}&rdquo;
                          </p>
                        ) : (
                          <p className="text-2xs text-[hsl(var(--text-secondary))] opacity-60 italic">
                            Sin frase o versículo
                          </p>
                        )}
                        <div className="flex items-center gap-2 text-2xs text-[hsl(var(--text-secondary))] pt-0.5">
                          <span
                            className={`inline-flex items-center gap-1 font-medium ${
                              profile.bio_full
                                ? "text-[hsl(var(--primary))]"
                                : "opacity-60"
                            }`}
                          >
                            <BookOpen size={10} />
                            {profile.bio_full ? "Historia redactada" : "Sin historia detallada"}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Card Actions */}
                    <div className="mt-4 pt-3 border-t border-[hsl(var(--border))]/60 dark:border-white/5 flex items-center justify-between">
                      <Link
                        href={`/pastores/${profile.slug}`}
                        target="_blank"
                        className="inline-flex items-center gap-1 text-2xs font-semibold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"
                      >
                        <ExternalLink size={11} /> Ver perfil
                      </Link>
                      <button
                        onClick={() => openDrawer(profile)}
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 hover:bg-[hsl(var(--primary))/0.15] text-[hsl(var(--text-primary))] dark:text-white hover:text-[hsl(var(--primary))] text-2xs font-bold uppercase transition-all"
                      >
                        <Pencil size={11} /> Editar
                      </button>
                    </div>
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
                    <div className="relative w-10 h-10 rounded-xl overflow-hidden bg-[hsl(var(--surface-2))] shrink-0">
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
                        {profile.is_main_pastor && <Sparkles size={11} className="text-[hsl(var(--primary))]" />}
                        {profile.bio_full && (
                          <span className="text-3xs bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] px-1.5 py-0.5 rounded font-medium">
                            Historia ✓
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-[hsl(var(--text-secondary))]">{profile.role || "Pastor"}</p>
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
                      <th className="text-left px-4 py-3 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Foto</th>
                      <th className="text-left px-4 py-3 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Nombre</th>
                      <th className="text-left px-4 py-3 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Rol</th>
                      <th className="text-left px-4 py-3 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Historia</th>
                      <th className="text-left px-4 py-3 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Principal</th>
                      <th className="text-right px-4 py-3 text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginated.map((profile) => (
                      <tr key={profile.id} className="border-b border-[hsl(var(--border))]/50 dark:border-white/[0.03] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] transition-colors">
                        <td className="px-4 py-3">
                          <div className="relative w-8 h-8 rounded-lg overflow-hidden bg-[hsl(var(--surface-2))]">
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
                          {profile.bio_full ? (
                            <span className="inline-flex items-center gap-1 text-2xs font-semibold text-[hsl(var(--primary))]">
                              <Check size={11} /> Redactada
                            </span>
                          ) : (
                            <span className="text-2xs text-[hsl(var(--text-secondary))] opacity-60">Pendiente</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {profile.is_main_pastor ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] text-2xs font-semibold">
                              <Check size={10} /> Sí
                            </span>
                          ) : (
                            <span className="text-2xs text-[hsl(var(--text-secondary))]">No</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => openDrawer(profile)}
                            className="p-1.5 rounded-lg hover:bg-[hsl(var(--primary))/0.1] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors"
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
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={closeDrawer}
          />
          <div className="relative w-full max-w-2xl bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-l border-[hsl(var(--border))] dark:border-white/[0.06] shadow-2xl overflow-y-auto">
            <div className="sticky top-0 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-b border-[hsl(var(--border))] dark:border-white/[0.06] px-6 py-4 flex items-center justify-between z-10">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] flex items-center justify-center">
                  <Pencil size={15} />
                </div>
                <div>
                  <h2 className="text-sm font-bold uppercase tracking-wider text-[hsl(var(--text-primary))] dark:text-white">
                    Editar perfil e historia
                  </h2>
                  <Link
                    href={`/pastores/${editing.slug}`}
                    target="_blank"
                    className="inline-flex items-center gap-1 text-3xs text-[hsl(var(--primary))] hover:underline font-mono"
                  >
                    /pastores/{editing.slug} <ExternalLink size={9} />
                  </Link>
                </div>
              </div>
              <button
                onClick={closeDrawer}
                className="w-8 h-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 transition-all"
              >
                <X size={14} />
              </button>
            </div>

            <form onSubmit={handleSave} className="p-6 space-y-5">
              {error && (
                <div className="p-3 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-xs text-[hsl(var(--destructive))]">
                  {error}
                </div>
              )}
              {successMsg && (
                <div className="p-3 rounded-xl bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/20 text-xs text-green-700 dark:text-green-400 flex items-center gap-2">
                  <Check size={14} />
                  {successMsg}
                </div>
              )}

              {/* Nombre (Editable) */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5">
                  Nombre Completo *
                </label>
                <input
                  name="name"
                  type="text"
                  required
                  value={editing.name}
                  onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                  placeholder="Ej: Pastor Luis Ricardo"
                  className="w-full px-4 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                />
              </div>

              {/* Rol (Editable) */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5">
                  Rol o Cargo Ministerial
                </label>
                <input
                  name="role"
                  type="text"
                  value={editing.role || ""}
                  onChange={(e) => setEditing({ ...editing, role: e.target.value })}
                  placeholder="Ej: Pastor Principal, Pastora de Familias, Pastor..."
                  className="w-full px-4 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                />
              </div>

              {/* Photo URL */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5">
                  Fotografía del perfil
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
                      placeholder="URL de la foto o selecciona desde la galería..."
                      className="w-full pl-9 pr-4 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setMediaPickerTarget("edit");
                      setMediaPickerOpen(true);
                    }}
                    className="px-3 py-2 rounded-xl bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))/0.2] transition-colors text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 shrink-0"
                  >
                    <ImageIcon size={14} /> Seleccionar
                  </button>
                </div>
                {editing.photo_url && (
                  <div className="mt-2 relative w-20 h-24 rounded-xl overflow-hidden border border-[hsl(var(--border))] dark:border-white/10">
                    <Image src={editing.photo_url} alt="Preview" fill className="object-cover" sizes="80px" />
                  </div>
                )}
              </div>

              {/* Bio short (Versículo / Frase) */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5 flex items-center gap-1.5">
                  <Quote size={12} /> Frase Lema o Versículo Bíblico (Tarjeta y Cita)
                </label>
                <textarea
                  name="bio_short"
                  defaultValue={editing.bio_short || ""}
                  rows={2}
                  placeholder="Breve descripción o versículo lema para la tarjeta..."
                  className="w-full px-4 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] resize-none"
                />
              </div>

              {/* Bio full (Historia completa) */}
              <div>
                <label className="block text-2xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1.5 flex items-center gap-1.5">
                  <BookOpen size={12} /> Historia Completa y Testimonio de Vida
                </label>
                <textarea
                  name="bio_full"
                  defaultValue={editing.bio_full || ""}
                  rows={6}
                  placeholder="Historia detallada del pastor, su llamado y testimonio (soporta HTML)..."
                  className="w-full px-4 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] font-sans"
                />
                <p className="text-3xs text-[hsl(var(--text-secondary))] mt-1">
                  Se renderiza en la sección &quot;Su Historia&quot; de <code className="bg-[hsl(var(--surface-3))] px-1 py-0.5 rounded">/pastores/{editing.slug}</code>.
                </p>
              </div>

              {/* Social */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-3xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1 flex items-center gap-1">
                    <Instagram size={11} /> Instagram
                  </label>
                  <input
                    name="social_instagram"
                    type="text"
                    value={editing.social_instagram || ""}
                    onChange={(e) => setEditing({ ...editing, social_instagram: e.target.value })}
                    placeholder="@usuario o https://instagram.com/..."
                    className="w-full px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
                <div>
                  <label className="block text-3xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1 flex items-center gap-1">
                    <Facebook size={11} /> Facebook
                  </label>
                  <input
                    name="social_facebook"
                    type="text"
                    value={editing.social_facebook || ""}
                    onChange={(e) => setEditing({ ...editing, social_facebook: e.target.value })}
                    placeholder="@usuario o https://facebook.com/..."
                    className="w-full px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
                <div>
                  <label className="block text-3xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))] mb-1 flex items-center gap-1">
                    <Twitter size={11} /> X (Twitter)
                  </label>
                  <input
                    name="social_twitter"
                    type="text"
                    value={editing.social_twitter || ""}
                    onChange={(e) => setEditing({ ...editing, social_twitter: e.target.value })}
                    placeholder="@usuario o https://x.com/..."
                    className="w-full px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Settings box */}
              <div className="p-4 rounded-xl bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] border border-[hsl(var(--border))] space-y-3">
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
                    <p className="text-2xs text-[hsl(var(--text-secondary))]">
                      Aparece resaltado con insignia dorada en la web pública
                    </p>
                  </div>
                </label>

                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    name="is_pastoral_published"
                    type="checkbox"
                    defaultChecked={editing.is_pastoral_published !== false}
                    className="w-4 h-4 rounded border-[hsl(var(--border))] dark:border-white/20 text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))/0.3]"
                  />
                  <div>
                    <span className="text-sm font-medium text-[hsl(var(--text-primary))] dark:text-white">
                      Publicado en Sitio Web
                    </span>
                    <p className="text-2xs text-[hsl(var(--text-secondary))]">
                      Visible en el catálogo público y su enlace
                    </p>
                  </div>
                </label>

                <div className="pt-2 border-t border-[hsl(var(--border))]/50 flex items-center justify-between">
                  <label className="text-2xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))]">
                    Orden de aparición
                  </label>
                  <input
                    name="pastoral_sort_order"
                    type="number"
                    value={editing.pastoral_sort_order ?? 0}
                    onChange={(e) => setEditing({ ...editing, pastoral_sort_order: parseInt(e.target.value) || 0 })}
                    min="0"
                    className="w-20 px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm text-center font-mono focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-3 pt-4 border-t border-[hsl(var(--border))] dark:border-white/[0.06]">
                <button
                  type="button"
                  onClick={closeDrawer}
                  className="flex-1 py-2.5 rounded-xl bg-[hsl(var(--surface-2))] dark:bg-white/5 text-sm font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 py-2.5 rounded-xl bg-[hsl(var(--primary))] text-white text-sm font-bold uppercase tracking-wider hover:opacity-90 disabled:opacity-50 transition-all shadow-md shadow-[hsl(var(--primary))/0.2]"
                >
                  {saving ? "Guardando..." : "Guardar Cambios"}
                </button>
              </div>

              {/* Danger Zone: Remove pastor */}
              <div className="pt-4 border-t border-red-500/20">
                {confirmDeleteId === editing.id ? (
                  <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 space-y-3">
                    <p className="text-xs text-red-600 dark:text-red-400 font-semibold">
                      ¿Seguro que deseas remover a {editing.name} del equipo pastoral?
                    </p>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleDeletePastor(editing.id)}
                        disabled={saving}
                        className="px-3 py-1.5 rounded-lg bg-red-600 text-white text-xs font-bold uppercase tracking-wider hover:bg-red-700 transition-colors"
                      >
                        {saving ? "Removiendo..." : "Sí, remover"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmDeleteId(null)}
                        className="px-3 py-1.5 rounded-lg bg-[hsl(var(--surface-2))] text-xs font-medium text-[hsl(var(--text-secondary))]"
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setConfirmDeleteId(editing.id)}
                    className="w-full py-2.5 rounded-xl border border-red-500/30 hover:bg-red-500/10 text-red-600 dark:text-red-400 text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2"
                  >
                    <Trash2 size={13} />
                    Remover del equipo pastoral
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Add / Create Drawer ── */}
      {drawerMode === "add" && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={closeDrawer}
          />
          <div className="relative w-full max-w-xl bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-l border-[hsl(var(--border))] dark:border-white/[0.06] shadow-2xl overflow-y-auto">
            <div className="sticky top-0 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border-b border-[hsl(var(--border))] dark:border-white/[0.06] px-6 py-4 flex items-center justify-between z-10">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] flex items-center justify-center">
                  <UserPlus size={16} />
                </div>
                <h2 className="text-sm font-bold uppercase tracking-wider text-[hsl(var(--text-primary))] dark:text-white">
                  Nuevo Líder Pastoral
                </h2>
              </div>
              <button
                onClick={closeDrawer}
                className="w-8 h-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 transition-all"
              >
                <X size={14} />
              </button>
            </div>

            {/* Sub-tabs: Crear desde cero vs Vincular */}
            <div className="flex border-b border-[hsl(var(--border))] dark:border-white/10 px-6 pt-2">
              <button
                type="button"
                onClick={() => setAddTab("create")}
                className={`py-2.5 px-4 text-xs font-bold uppercase tracking-wider border-b-2 transition-all ${
                  addTab === "create"
                    ? "border-[hsl(var(--primary))] text-[hsl(var(--primary))]"
                    : "border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                }`}
              >
                Crear Nuevo Pastor
              </button>
              <button
                type="button"
                onClick={() => setAddTab("link")}
                className={`py-2.5 px-4 text-xs font-bold uppercase tracking-wider border-b-2 transition-all ${
                  addTab === "link"
                    ? "border-[hsl(var(--primary))] text-[hsl(var(--primary))]"
                    : "border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                }`}
              >
                Vincular de la Congregación
              </button>
            </div>

            <div className="p-6">
              {error && (
                <div className="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-xs text-[hsl(var(--destructive))]">
                  {error}
                </div>
              )}
              {successMsg && (
                <div className="mb-4 p-3 rounded-xl bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/20 text-xs text-green-700 dark:text-green-400 flex items-center gap-2">
                  <Check size={14} />
                  {successMsg}
                </div>
              )}

              {/* Tab 1: Formulario Completo para Crear Pastor */}
              {addTab === "create" && (
                <form onSubmit={handleCreatePastor} className="space-y-4">
                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                      Nombre Completo *
                    </label>
                    <input
                      type="text"
                      required
                      value={newPastor.name}
                      onChange={(e) => setNewPastor({ ...newPastor, name: e.target.value })}
                      placeholder="Ej: Pastor David Gómez"
                      className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                    />
                  </div>

                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                      Rol o Cargo Ministerial
                    </label>
                    <input
                      type="text"
                      value={newPastor.role}
                      onChange={(e) => setNewPastor({ ...newPastor, role: e.target.value })}
                      placeholder="Ej: Pastor Principal, Pastora de Jóvenes, Pastor..."
                      className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                    />
                  </div>

                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                      Fotografía del Pastor
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newPastor.photo_url}
                        onChange={(e) => setNewPastor({ ...newPastor, photo_url: e.target.value })}
                        placeholder="URL de la fotografía..."
                        className="flex-1 px-3 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          setMediaPickerTarget("create");
                          setMediaPickerOpen(true);
                        }}
                        className="px-3 py-2 rounded-xl bg-[hsl(var(--primary))/0.1] text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))/0.2] text-xs font-bold uppercase tracking-wider transition-colors shrink-0 flex items-center gap-1.5"
                      >
                        <ImageIcon size={14} /> Seleccionar
                      </button>
                    </div>
                    {newPastor.photo_url && (
                      <div className="mt-2 relative w-16 h-20 rounded-xl overflow-hidden border border-[hsl(var(--border))]">
                        <Image src={newPastor.photo_url} alt="Preview" fill className="object-cover" sizes="64px" />
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1 flex items-center gap-1.5">
                      <Quote size={12} /> Frase Lema o Versículo Bíblico
                    </label>
                    <textarea
                      rows={2}
                      value={newPastor.bio_short}
                      onChange={(e) => setNewPastor({ ...newPastor, bio_short: e.target.value })}
                      placeholder="Extracto inspirador para la tarjeta del pastor..."
                      className="w-full px-3.5 py-2 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] resize-none"
                    />
                  </div>

                  <div>
                    <label className="block text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1 flex items-center gap-1.5">
                      <BookOpen size={12} /> Historia Completa y Testimonio de Vida
                    </label>
                    <textarea
                      rows={5}
                      value={newPastor.bio_full}
                      onChange={(e) => setNewPastor({ ...newPastor, bio_full: e.target.value })}
                      placeholder="Redacta la historia completa del pastor y su llamado (soporta párrafos normales y HTML)..."
                      className="w-full px-3.5 py-2.5 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-xs focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <label className="block text-3xs font-bold uppercase text-[hsl(var(--text-secondary))] mb-1">Instagram</label>
                      <input
                        type="text"
                        value={newPastor.social_instagram}
                        onChange={(e) => setNewPastor({ ...newPastor, social_instagram: e.target.value })}
                        placeholder="@usuario o https://..."
                        className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-3xs font-bold uppercase text-[hsl(var(--text-secondary))] mb-1">Facebook</label>
                      <input
                        type="text"
                        value={newPastor.social_facebook}
                        onChange={(e) => setNewPastor({ ...newPastor, social_facebook: e.target.value })}
                        placeholder="@usuario o https://..."
                        className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-3xs font-bold uppercase text-[hsl(var(--text-secondary))] mb-1">X (Twitter)</label>
                      <input
                        type="text"
                        value={newPastor.social_twitter}
                        onChange={(e) => setNewPastor({ ...newPastor, social_twitter: e.target.value })}
                        placeholder="@usuario o https://..."
                        className="w-full px-2.5 py-1.5 rounded-lg border border-[hsl(var(--border))] text-xs"
                      />
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-xl bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] border border-[hsl(var(--border))]">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={newPastor.is_main_pastor}
                        onChange={(e) => setNewPastor({ ...newPastor, is_main_pastor: e.target.checked })}
                        className="w-4 h-4 rounded text-[hsl(var(--primary))]"
                      />
                      <span className="text-xs font-bold text-[hsl(var(--text-primary))]">Pastor Principal</span>
                    </label>

                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={newPastor.is_pastoral_published}
                        onChange={(e) => setNewPastor({ ...newPastor, is_pastoral_published: e.target.checked })}
                        className="w-4 h-4 rounded text-[hsl(var(--primary))]"
                      />
                      <span className="text-xs font-bold text-[hsl(var(--text-primary))]">Publicado</span>
                    </label>

                    <div className="flex items-center gap-1.5">
                      <span className="text-2xs font-bold text-[hsl(var(--text-secondary))]">Orden:</span>
                      <input
                        type="number"
                        value={newPastor.pastoral_sort_order}
                        onChange={(e) => setNewPastor({ ...newPastor, pastoral_sort_order: parseInt(e.target.value) || 0 })}
                        className="w-14 px-2 py-1 rounded border text-xs text-center font-mono"
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-3 pt-3 border-t border-[hsl(var(--border))]">
                    <button
                      type="button"
                      onClick={closeDrawer}
                      className="px-4 py-2 rounded-xl bg-[hsl(var(--surface-2))] text-xs font-medium text-[hsl(var(--text-secondary))]"
                    >
                      Cancelar
                    </button>
                    <button
                      type="submit"
                      disabled={saving}
                      className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wider hover:opacity-90 disabled:opacity-50 transition-all shadow-md shadow-[hsl(var(--primary))/0.2]"
                    >
                      {saving ? (
                        <>
                          <Loader2 size={13} className="animate-spin" /> Creando...
                        </>
                      ) : (
                        <>
                          <Check size={13} /> Crear Pastor
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}

              {/* Tab 2: Vincular Persona Existente de CRM */}
              {addTab === "link" && (
                <div className="space-y-4">
                  <p className="text-xs text-[hsl(var(--text-secondary))]">
                    Busca a una persona ya registrada en el CRM de la iglesia para elevarla al equipo pastoral.
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
                        <div className="space-y-2 max-h-80 overflow-y-auto">
                          {addResults.map((persona: PersonaSearchResult) => (
                            <div
                              key={persona.id}
                              className="flex items-center justify-between p-3 rounded-xl bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] border border-[hsl(var(--border))] dark:border-white/[0.04]"
                            >
                              <div>
                                <p className="text-sm font-medium text-[hsl(var(--text-primary))] dark:text-white">
                                  {persona.nombre_completo || persona.name}
                                </p>
                                <p className="text-2xs text-[hsl(var(--text-secondary))]">
                                  {persona.church_role || "Persona"}
                                </p>
                              </div>
                              <button
                                onClick={() => handleAddLeader(persona.id)}
                                disabled={saving}
                                className="px-3 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-white text-2xs font-bold uppercase tracking-wider hover:opacity-90 disabled:opacity-50 transition-all"
                              >
                                {saving ? "..." : "Agregar"}
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}

                  <div className="flex pt-4 border-t border-[hsl(var(--border))]">
                    <button
                      type="button"
                      onClick={closeDrawer}
                      className="flex-1 py-2 rounded-xl bg-[hsl(var(--surface-2))] text-xs font-medium text-[hsl(var(--text-secondary))]"
                    >
                      Cerrar
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Media Picker ── */}
      {mediaPickerOpen && (
        <MediaPicker
          open
          token={token}
          selectedUrl={
            mediaPickerTarget === "edit"
              ? editing?.photo_url || undefined
              : newPastor.photo_url || undefined
          }
          onClose={() => setMediaPickerOpen(false)}
          onSelect={(item) => {
            const url = typeof item === "string" ? item : (item as { url?: string }).url || "";
            if (url) {
              if (mediaPickerTarget === "edit" && editing) {
                setEditing({ ...editing, photo_url: url });
              } else if (mediaPickerTarget === "create") {
                setNewPastor((prev) => ({ ...prev, photo_url: url }));
              }
            }
            setMediaPickerOpen(false);
          }}
        />
      )}
    </div>
  );
}

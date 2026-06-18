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
import AdminHero from "@/components/admin/AdminHero";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import {
  PastoralProfile,
  getCmsPastoralTeam,
  updateCmsPastoralProfile,
} from "@/lib/cms/v2";

type DrawerMode = "edit" | "add" | null;

export default function PastoralTeamPage() {
  const { token } = useAuth();
  const [profiles, setProfiles] = useState<PastoralProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [drawerMode, setDrawerMode] = useState<DrawerMode>(null);
  const [editing, setEditing] = useState<PastoralProfile | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [addSearch, setAddSearch] = useState("");
  const [addResults, setAddResults] = useState<any[]>([]);
  const [searchingAdd, setSearchingAdd] = useState(false);

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
    const photoUrl = formData.get("photo_url") as string;
    const bioShort = formData.get("bio_short") as string;
    const bioFull = formData.get("bio_full") as string;
    const socialInstagram = formData.get("social_instagram") as string;
    const socialFacebook = formData.get("social_facebook") as string;
    const socialTwitter = formData.get("social_twitter") as string;
    const isMainPastor = formData.get("is_main_pastor") === "on";

    const data: Record<string, any> = {};

    if (photoUrl !== editing.photo_url) data.photo_url = photoUrl || null;
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
        { is_pastoral_leader: true } as any,
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
      const res = await apiFetch<any[]>(
        `/crm/v2/personas?q=${encodeURIComponent(q)}&limit=10`,
        { token }
      );
      const existingIds = new Set(profiles.map((p) => p.id));
      setAddResults(
        (res || []).filter(
          (p: any) => !existingIds.has(p.id) && !p.is_pastoral_leader
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
      <AdminHero
        title="Equipo Pastoral"
        description="Gestiona los perfiles del equipo pastoral visibles en la página pública."
        badge="CMS"
      />

      {/* ── Actions Bar ── */}
      <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-8 xl:px-12 py-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="relative flex-1 max-w-sm">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
              placeholder="Buscar por nombre..."
              className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">
              {filtered.length} líderes
            </span>
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
              className="mx-auto text-slate-300 dark:text-slate-600 mb-4"
            />
            <p className="text-slate-400">
              {search
                ? "No se encontraron líderes con ese nombre."
                : "No hay líderes pastorales registrados. ¡Agrega el primero!"}
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {paginated.map((profile) => (
                <div
                  key={profile.id}
                  className="group relative bg-white dark:bg-[#0f1117] rounded-xl border border-slate-200/70 dark:border-white/[0.06] p-4 flex items-start gap-4 hover:shadow-lg hover:-translate-y-0.5 transition-all"
                >
                  {/* Avatar */}
                  <div className="relative w-14 h-14 rounded-full overflow-hidden bg-slate-100 dark:bg-[#0a0c12] shrink-0 ring-2 ring-slate-200/50 dark:ring-white/[0.06]">
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
                        <span className="text-lg font-bold text-[hsl(var(--primary))/0.3]">
                          {profile.name.charAt(0)}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-sm text-slate-800 dark:text-white truncate">
                        {profile.name}
                      </h3>
                      {profile.is_main_pastor && (
                        <Sparkles
                          size={12}
                          className="text-[hsl(var(--primary))] shrink-0"
                        />
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {profile.role || "Pastor"}
                    </p>
                    {/* Social indicators */}
                    <div className="flex items-center gap-2 mt-2">
                      {profile.social_instagram && (
                        <Instagram
                          size={12}
                          className="text-slate-300 dark:text-slate-600"
                        />
                      )}
                      {profile.social_facebook && (
                        <Facebook
                          size={12}
                          className="text-slate-300 dark:text-slate-600"
                        />
                      )}
                      {profile.social_twitter && (
                        <Twitter
                          size={12}
                          className="text-slate-300 dark:text-slate-600"
                        />
                      )}
                      {!profile.social_instagram &&
                        !profile.social_facebook &&
                        !profile.social_twitter && (
                          <span className="text-[9px] text-slate-300 dark:text-slate-600">
                            Sin redes
                          </span>
                        )}
                    </div>
                  </div>

                  {/* Edit button */}
                  <button
                    onClick={() => openDrawer(profile)}
                    className="absolute top-3 right-3 w-7 h-7 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))/0.1] opacity-0 group-hover:opacity-100 transition-all"
                    aria-label="Editar"
                  >
                    <Pencil size={12} />
                  </button>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3 mt-8">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="w-9 h-9 rounded-xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 flex items-center justify-center text-slate-400 disabled:opacity-30 hover:bg-slate-50 dark:hover:bg-white/10 transition-all"
                >
                  <ChevronLeft size={16} />
                </button>
                <span className="text-xs font-bold text-slate-400">
                  {page + 1} / {totalPages}
                </span>
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="w-9 h-9 rounded-xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 flex items-center justify-center text-slate-400 disabled:opacity-30 hover:bg-slate-50 dark:hover:bg-white/10 transition-all"
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
          <div className="relative w-full max-w-lg bg-white dark:bg-[#0a0c12] border-l border-slate-200 dark:border-white/[0.06] shadow-2xl overflow-y-auto">
            <div className="sticky top-0 bg-white dark:bg-[#0a0c12] border-b border-slate-200 dark:border-white/[0.06] px-6 py-4 flex items-center justify-between z-10">
              <h2 className="text-sm font-bold uppercase tracking-wider">
                Editar perfil
              </h2>
              <button
                onClick={closeDrawer}
                className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10 transition-all"
              >
                <X size={14} />
              </button>
            </div>

            <form onSubmit={handleSave} className="p-6 space-y-5">
              {error && (
                <div className="p-3 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-xs text-red-600 dark:text-red-400">
                  {error}
                </div>
              )}
              {successMsg && (
                <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                  <Check size={14} />
                  {successMsg}
                </div>
              )}

              {/* Nombre (readonly) */}
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
                  Nombre
                </label>
                <p className="text-sm font-medium text-slate-800 dark:text-white">
                  {editing.name}
                </p>
              </div>

              {/* Rol (readonly) */}
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
                  Rol
                </label>
                <p className="text-sm text-slate-500">
                  {editing.role || "Pastor"}
                </p>
              </div>

              {/* Photo URL */}
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
                  URL de foto
                </label>
                <div className="relative">
                  <ImageIcon
                    size={14}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                  />
                  <input
                    name="photo_url"
                    type="url"
                    defaultValue={editing.photo_url || ""}
                    placeholder="https://ejemplo.com/foto.jpg"
                    className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Bio short */}
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
                  Biografía corta
                </label>
                <textarea
                  name="bio_short"
                  defaultValue={editing.bio_short || ""}
                  rows={2}
                  placeholder="Breve descripción para la tarjeta..."
                  className="w-full px-4 py-2 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] resize-none"
                />
              </div>

              {/* Bio full */}
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
                  Historia completa (HTML)
                </label>
                <textarea
                  name="bio_full"
                  defaultValue={editing.bio_full || ""}
                  rows={4}
                  placeholder="Historia completa del pastor (soporta HTML)..."
                  className="w-full px-4 py-2 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3] resize-none font-mono"
                />
              </div>

              {/* Social */}
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5 flex items-center gap-1.5">
                    <Instagram size={12} /> Instagram URL
                  </label>
                  <input
                    name="social_instagram"
                    type="url"
                    defaultValue={editing.social_instagram || ""}
                    placeholder="https://instagram.com/..."
                    className="w-full px-4 py-2 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5 flex items-center gap-1.5">
                    <Facebook size={12} /> Facebook URL
                  </label>
                  <input
                    name="social_facebook"
                    type="url"
                    defaultValue={editing.social_facebook || ""}
                    placeholder="https://facebook.com/..."
                    className="w-full px-4 py-2 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5 flex items-center gap-1.5">
                    <Twitter size={12} /> X (Twitter) URL
                  </label>
                  <input
                    name="social_twitter"
                    type="url"
                    defaultValue={editing.social_twitter || ""}
                    placeholder="https://x.com/..."
                    className="w-full px-4 py-2 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
                  />
                </div>
              </div>

              {/* Toggle is_main_pastor */}
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  name="is_main_pastor"
                  type="checkbox"
                  defaultChecked={editing.is_main_pastor}
                  className="w-4 h-4 rounded border-slate-300 dark:border-white/20 text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))/0.3]"
                />
                <div>
                  <span className="text-sm font-medium text-slate-800 dark:text-white">
                    Pastor Principal
                  </span>
                  <p className="text-[10px] text-slate-400">
                    Aparece resaltado en la página pública
                  </p>
                </div>
              </label>

              {/* Actions */}
              <div className="flex items-center gap-3 pt-4 border-t border-slate-200 dark:border-white/[0.06]">
                <button
                  type="button"
                  onClick={closeDrawer}
                  className="flex-1 py-2.5 rounded-xl bg-slate-100 dark:bg-white/5 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-white/10 transition-all"
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
          <div className="relative w-full max-w-lg bg-white dark:bg-[#0a0c12] border-l border-slate-200 dark:border-white/[0.06] shadow-2xl overflow-y-auto">
            <div className="sticky top-0 bg-white dark:bg-[#0a0c12] border-b border-slate-200 dark:border-white/[0.06] px-6 py-4 flex items-center justify-between z-10">
              <h2 className="text-sm font-bold uppercase tracking-wider">
                Agregar líder pastoral
              </h2>
              <button
                onClick={closeDrawer}
                className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10 transition-all"
              >
                <X size={14} />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {successMsg && (
                <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-xs text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                  <Check size={14} />
                  {successMsg}
                </div>
              )}
              <p className="text-xs text-slate-400">
                Busca una persona existente para agregarla como líder pastoral.
              </p>

              <div className="relative">
                <Search
                  size={16}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <input
                  type="text"
                  value={addSearch}
                  onChange={(e) => searchPersonas(e.target.value)}
                  placeholder="Buscar por nombre (mín. 3 caracteres)..."
                  className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.3]"
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
                    <p className="text-center py-8 text-xs text-slate-400">
                      {addSearch.trim()
                        ? "No se encontraron personas disponibles."
                        : "Escribe para buscar..."}
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {addResults.map((persona: any) => (
                        <div
                          key={persona.id}
                          className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/[0.04]"
                        >
                          <div>
                            <p className="text-sm font-medium text-slate-800 dark:text-white">
                              {persona.nombre_completo || persona.name}
                            </p>
                            <p className="text-[10px] text-slate-400">
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
                  className="flex-1 py-2.5 rounded-xl bg-slate-100 dark:bg-white/5 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-white/10 transition-all"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

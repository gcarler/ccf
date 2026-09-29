"use client";

import React, { useEffect, useState, useCallback, useMemo, useRef } from "react";
import OptimizedImage from "@/components/ui/OptimizedImage";
import {
  Play,
  Calendar,
  Youtube,
  RefreshCw,
  ExternalLink,
  Search,
  X,
  Check,
  Link2,
  MessageCircle,
  BookOpen,
  Eye,
  User,
  SlidersHorizontal,
} from "lucide-react";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import { toast } from "sonner";
import SermonDetailDrawer, {
  YTVideo,
  extractPreacherName,
} from "@/components/public/SermonDetailDrawer";

import { apiFetch } from "@/lib/http";
import { formatDate } from "@/lib/format";
import { safeJsonParse } from "@/lib/safeJson";
import { normalizeThumbnailOverrides, resolveThumbnailUrl } from "./thumbnail-overrides";

interface YTResponse {
  videos: YTVideo[];
  total: number;
  channel: string;
  error?: string;
}

/* ── Helpers ── */
function timeAgo(iso: string) {
  if (!iso) return "";
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days === 0) return "hoy";
  if (days === 1) return "ayer";
  if (days < 7) return `hace ${days} días`;
  if (days < 30) return `hace ${Math.floor(days / 7)} sem.`;
  if (days < 365) return `hace ${Math.floor(days / 30)} meses`;
  return `hace ${Math.floor(days / 365)} año${Math.floor(days / 365) > 1 ? "s" : ""}`;
}

function formatViews(n: number) {
  if (!n) return "";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return `${n}`;
}

/* Limpia la descripción: quita todo el bloque de redes sociales */
function cleanDesc(raw: string) {
  const cutMarkers = ["¡NO OLVIDES", "REDES SOCIALES", "Instagram:", "Facebook:", "Visita nuestra página"];
  let s = raw ?? "";
  for (const m of cutMarkers) {
    const i = s.indexOf(m);
    if (i > 0) s = s.substring(0, i);
  }
  return s.trim();
}

/* ── Historial en localStorage ── */
const LS_KEY = "ccf-predicas-watched";
function loadWatched(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) ?? "{}");
  } catch {
    return {};
  }
}
function saveWatched(w: Record<string, string>) {
  localStorage.setItem(LS_KEY, JSON.stringify(w));
}

/* ── Skeleton ── */
function SkeletonCard() {
  return (
    <div
      className="rounded-2xl overflow-hidden animate-pulse"
      style={{ background: "var(--site-surface-container)" }}
    >
      <div className="aspect-video bg-site-outline-variant/20" />
      <div className="p-4 space-y-2">
        <div className="h-4 bg-site-outline-variant/20 rounded w-3/4" />
        <div className="h-3 bg-site-outline-variant/10 rounded w-1/2" />
      </div>
    </div>
  );
}

/* ── Card de video ── */
function VideoCard({
  video,
  featured = false,
  watched,
  onPlay,
  onShare,
  onCopy,
  copied,
  featuredBadge,
  shareWhatsapp,
  copyLinkLabel,
}: {
  video: YTVideo;
  featured?: boolean;
  watched: boolean;
  onPlay: () => void;
  onShare: () => void;
  onCopy: () => void;
  copied: boolean;
  featuredBadge: string;
  shareWhatsapp: string;
  copyLinkLabel: string;
}) {
  const [imgErr, setImgErr] = useState(false);
  const desc = cleanDesc(video.description);
  const preacher = extractPreacherName(video.title);

  return (
    <div
      className={`group relative rounded-2xl overflow-hidden transition-all duration-300 hover:-translate-y-1 cursor-pointer border ${
        featured
          ? "border-site-primary/40 ring-1 ring-site-primary/30"
          : "border-site-outline-variant/15 hover:border-site-outline-variant/30"
      }`}
      style={{
        background: "var(--site-surface-container)",
        boxShadow: featured ? "0 8px 40px -8px var(--site-glow-intense)" : undefined,
      }}
      onClick={onPlay}
    >
      {/* Thumbnail */}
      <div className="relative overflow-hidden aspect-video bg-site-surface-container-lowest">
        <OptimizedImage
          src={imgErr ? video.thumbnail_mq : video.thumbnail_hq}
          alt={video.title}
          fill
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
          onError={() => setImgErr(true)}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/15 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

        {/* Play button overlay */}
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300">
          <div
            className="w-14 h-14 sm:w-16 sm:h-16 rounded-full flex items-center justify-center backdrop-blur-md border border-white/30 shadow-2xl transition-transform group-hover:scale-105"
            style={{ background: "var(--site-cta-gradient, #2563eb)" }}
          >
            <Play size={26} className="text-white ml-1" fill="white" />
          </div>
        </div>

        {/* Badges superiores */}
        <div className="absolute top-2.5 left-2.5 flex gap-1.5 flex-wrap">
          {featured && (
            <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-black/70 text-white text-3xs font-bold uppercase tracking-wider backdrop-blur-md">
              <Youtube size={10} className="text-red-500" /> {featuredBadge || "Destacado"}
            </span>
          )}
          {watched && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-black/70 text-white text-3xs font-bold uppercase tracking-wider backdrop-blur-md">
              <Eye size={10} /> Visto
            </span>
          )}
        </div>

        {/* Tiempo transcurrido */}
        <span
          className="absolute bottom-2 right-2 px-2 py-0.5 rounded text-3xs font-semibold text-white backdrop-blur-md"
          style={{ background: "rgba(0,0,0,0.65)" }}
        >
          {timeAgo(video.published_at)}
        </span>
      </div>

      {/* Info */}
      <div className={`p-4 ${featured ? "md:p-5" : ""}`}>
        {/* Predicador */}
        <div className="flex items-center gap-1.5 text-site-primary text-3xs font-extrabold uppercase tracking-wider mb-1.5">
          <User size={11} className="shrink-0" />
          <span className="truncate">{preacher}</span>
        </div>

        <h3
          className={`font-bold text-site-on-surface group-hover:text-site-primary transition-colors leading-snug line-clamp-2 mb-2 ${
            featured ? "text-lg md:text-2xl" : "text-sm"
          }`}
        >
          {video.title}
        </h3>

        {featured && desc && (
          <p className="text-xs sm:text-sm text-site-on-surface-variant line-clamp-2 mb-3.5 leading-relaxed">
            {desc}
          </p>
        )}

        <div className="flex items-center justify-between gap-2 pt-1 border-t border-site-outline-variant/10">
          <div className="flex items-center gap-2.5 text-xs text-site-outline font-medium">
            <span className="flex items-center gap-1">
              <Calendar size={11} />
              {formatDate(video.published_at, { month: "short", day: "numeric", fallback: "" })}
            </span>
            {video.view_count > 0 && (
              <span className="flex items-center gap-1">
                <Eye size={11} /> {formatViews(video.view_count)}
              </span>
            )}
          </div>

          {/* Acciones rápidas */}
          <div className="flex items-center gap-1">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onShare();
              }}
              title={shareWhatsapp}
              className="p-1.5 rounded-lg hover:bg-site-primary/10 text-site-outline hover:text-site-on-surface transition-colors"
            >
              <MessageCircle size={14} />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onCopy();
              }}
              title={copyLinkLabel}
              className="p-1.5 rounded-lg hover:bg-site-primary/10 text-site-outline hover:text-site-primary transition-colors"
            >
              {copied ? <Check size={14} className="text-emerald-500" /> : <Link2 size={14} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Página principal ── */
export default function PredicasPage() {
  const feedPage = useCmsV2Page("sermons");
  const feedContent = feedPage?.blocks?.feed;
  const [data, setData] = useState<YTResponse | null>(null);
  const [loading, setLoad] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedPreacher, setSelectedPreacher] = useState<string>("Todos");
  const [drawerVideo, setDrawerVideo] = useState<YTVideo | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [watched, setWatched] = useState<Record<string, string>>({});
  const [copied, setCopied] = useState<string | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  /* Cargar historial */
  useEffect(() => {
    setWatched(loadWatched());
  }, []);

  /* Fetch videos vía apiFetch canónico */
  const load = useCallback(async () => {
    setLoad(true);
    setError(false);
    try {
      const res = await apiFetch<YTResponse>("/youtube/videos", { silent: true });
      setData(res);
    } catch {
      setError(true);
    } finally {
      setLoad(false);
    }
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  const feed = safeJsonParse<Record<string, unknown>>(feedContent?.content, {});
  const thumbnailOverrides = useMemo(
    () => normalizeThumbnailOverrides(feed.thumbnail_overrides ?? feedContent?.thumbnail_overrides),
    [feed.thumbnail_overrides, feedContent?.thumbnail_overrides]
  );
  const displayVideos = useMemo(
    () =>
      (data?.videos ?? []).map((video) => ({
        ...video,
        thumbnail_hq: resolveThumbnailUrl(video, thumbnailOverrides),
      })),
    [data?.videos, thumbnailOverrides]
  );

  const feedString = (key: string) => {
    const value = feed[key];
    return typeof value === "string" ? value : "";
  };

  const youtubeChannelUrl =
    typeof feedContent?.youtube_channel_url === "string"
      ? feedContent.youtube_channel_url
      : feedString("youtube_channel_url") || "https://www.youtube.com/@comunidadcristianalefaro";

  const heroEyebrow = feedString("hero_eyebrow") || "Alimento Espiritual";
  const heroTitleLead = feedString("hero_title_lead") || "Prédicas y";
  const heroTitleAccent = feedString("hero_title_accent") || "Mensajes de Fe";
  const heroDescription =
    feedString("hero_description") ||
    "Encuentra enseñanzas bíblicas semanales diseñadas para fortalecer tu fe, edificar tu familia y caminar en victoria en tu vida diaria.";
  const featuredBadge = feedString("featured_badge") || "Mensaje Central";
  const retryLabel = feedString("retry_label") || "Reintentar";
  const shareWhatsapp = feedString("share_whatsapp") || "Compartir en WhatsApp";
  const copyLinkLabel = feedString("copy_link") || "Copiar enlace";
  const copiedLabel = feedString("copied_label") || "¡Copiado!";
  const viewOnYoutube = feedString("view_on_youtube") || "Ver en YouTube";
  const watchedLabel = feedString("watched_label") || "escuchado";
  const searchPlaceholder =
    feedString("search_placeholder") || "Buscar por título, pasaje o predicador...";
  const featuredLabel = feedString("featured_label") || "Último Mensaje";
  const channelLinkLabel = feedString("channel_link_label") || "Canal de YouTube";
  const gridLabel = feedString("grid_label") || "Todas las Prédicas";
  const resultsLabel = feedString("results_label") || "Resultados encontrados";
  const moreVideosLabel = feedString("more_videos_label") || "mensajes disponibles";
  const ctaLabel = feedString("cta_label") || "Suscríbete en YouTube para más contenido";
  const emptyTitle = feedString("empty_title") || "No pudimos cargar los videos de YouTube";
  const emptyDescription =
    feedString("empty_description") ||
    "Por favor verifica tu conexión a internet o intenta nuevamente en unos instantes.";

  const hasHero = Boolean(heroTitleLead || heroTitleAccent || heroDescription || heroEyebrow);

  /* Extraer lista única de predicadores para los chips de filtro */
  const preachersList = useMemo(() => {
    const set = new Set<string>();
    displayVideos.forEach((v) => {
      const p = extractPreacherName(v.title);
      if (p && p !== "Comunidad Cristiana El Faro") {
        set.add(p);
      }
    });
    return ["Todos", ...Array.from(set)];
  }, [displayVideos]);

  /* Marcar visto + abrir Drawer lateral (0 modales) */
  const openPlayer = useCallback((video: YTVideo) => {
    setDrawerVideo(video);
    setIsDrawerOpen(true);
    setWatched((prev) => {
      const next = { ...prev, [video.id]: new Date().toISOString() };
      saveWatched(next);
      return next;
    });
  }, []);

  /* Compartir WhatsApp */
  const shareWA = useCallback((video: YTVideo) => {
    const text = encodeURIComponent(`🎙️ Te comparto esta prédica de Comunidad Cristiana El Faro:\n\n*${video.title}*\n${video.url}`);
    window.open(`https://wa.me/?text=${text}`, "_blank");
  }, []);

  /* Copiar link */
  const copyLink = useCallback(async (video: YTVideo) => {
    await navigator.clipboard.writeText(video.url);
    setCopied(video.id);
    toast.success("Enlace copiado al portapapeles");
    setTimeout(() => setCopied(null), 2000);
  }, []);

  /* Videos filtrados por búsqueda y por Predicador seleccionado */
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return displayVideos.filter((v) => {
      // Filtro por predicador
      if (selectedPreacher !== "Todos") {
        const p = extractPreacherName(v.title).toLowerCase();
        if (p !== selectedPreacher.toLowerCase()) return false;
      }

      // Filtro por texto
      if (!q) return true;
      const title = v.title.toLowerCase();
      const desc = v.description.toLowerCase();
      const preacher = extractPreacherName(v.title).toLowerCase();
      return title.includes(q) || desc.includes(q) || preacher.includes(q);
    });
  }, [displayVideos, search, selectedPreacher]);

  /* Conteo mensual de prédicas vistas */
  const viewedThisMonth = useMemo(() => {
    const now = new Date();
    return Object.values(watched).filter((d) => {
      const dt = new Date(d);
      return dt.getMonth() === now.getMonth() && dt.getFullYear() === now.getFullYear();
    }).length;
  }, [watched]);

  const featured = !search.trim() && selectedPreacher === "Todos" ? filtered[0] ?? null : null;
  const rest = !search.trim() && selectedPreacher === "Todos" ? filtered.slice(1) : filtered;

  return (
    <main
      className="min-h-screen pt-[88px] bg-site-surface text-site-on-surface"
      style={{
        background: "var(--site-surface, #fcfcfd)",
        color: "var(--site-on-surface, #1e1f21)",
      }}
    >
      {/* ── HERO ── */}
      {hasHero && (
        <section className="relative px-4 sm:px-6 md:px-8 xl:px-12 pt-10 sm:pt-14 pb-8 overflow-hidden border-b border-site-outline-variant/10">
          <div
            className="absolute -top-32 -right-32 w-[500px] h-[500px] rounded-full blur-3xl pointer-events-none opacity-60"
            style={{
              background: "radial-gradient(ellipse, var(--site-glow-subtle, rgba(37,99,235,0.15)) 0%, transparent 70%)",
            }}
          />
          <div className="max-w-7xl mx-auto relative z-10">
            {heroEyebrow && (
              <div className="flex items-center gap-3 mb-3.5">
                <span className="w-8 h-0.5 rounded-full" style={{ background: "var(--site-primary, #2563eb)" }} />
                <span
                  className="text-xs font-extrabold uppercase tracking-widest flex items-center gap-2"
                  style={{ color: "var(--site-primary, #2563eb)" }}
                >
                  <Youtube size={14} className="text-red-600" /> {heroEyebrow}
                </span>
              </div>
            )}

            {(heroTitleLead || heroTitleAccent) && (
              <h1 className="max-w-4xl font-black tracking-tight leading-[1.02] mb-3 text-3xl sm:text-5xl lg:text-6xl text-site-on-surface">
                {heroTitleLead && <>{heroTitleLead} </>}
                {heroTitleAccent && (
                  <span
                    className="italic"
                    style={{
                      background: "var(--site-cta-gradient, #2563eb)",
                      WebkitBackgroundClip: "text",
                      WebkitTextFillColor: "transparent",
                    }}
                  >
                    {heroTitleAccent}
                  </span>
                )}
              </h1>
            )}

            {heroDescription && (
              <p className="text-sm sm:text-base text-site-on-surface-variant max-w-2xl leading-relaxed mb-4 opacity-90">
                {heroDescription}
              </p>
            )}

            {/* Contador de vistas del mes */}
            {viewedThisMonth > 0 && watchedLabel && (
              <div
                className="inline-flex items-center gap-2 text-xs font-bold px-3 py-1 rounded-full mb-3 border"
                style={{
                  background: "var(--site-primary-container, rgba(37,99,235,0.08))",
                  borderColor: "var(--site-outline-variant, rgba(37,99,235,0.2))",
                  color: "var(--site-primary, #2563eb)",
                }}
              >
                <BookOpen size={13} />
                <span>
                  {viewedThisMonth} mensaje{viewedThisMonth !== 1 ? "s" : ""} {watchedLabel}
                  {viewedThisMonth !== 1 ? "s" : ""} este mes
                </span>
              </div>
            )}

            {/* Buscador reactivo */}
            <div className="relative max-w-lg mt-3">
              <Search
                size={16}
                className="absolute left-3.5 top-1/2 -translate-y-1/2 text-site-outline pointer-events-none opacity-60"
              />
              <input
                ref={searchRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={searchPlaceholder}
                className="w-full rounded-xl pl-10 pr-9 py-2.5 text-xs sm:text-sm text-site-on-surface placeholder:text-site-outline outline-none focus:ring-2 focus:ring-site-primary/40 transition-all border border-site-outline-variant/20"
                style={{ background: "var(--site-surface-container, #ffffff)" }}
              />
              {search && (
                <button
                  onClick={() => setSearch("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-site-outline hover:text-site-on-surface transition-colors"
                >
                  <X size={15} />
                </button>
              )}
            </div>

            {/* Chips Dinámicos de Filtro por Predicador */}
            {preachersList.length > 1 && (
              <div className="mt-5 space-y-2">
                <div className="flex items-center justify-between text-3xs font-extrabold uppercase tracking-wider text-site-on-surface-variant opacity-80">
                  <span className="flex items-center gap-1.5">
                    <SlidersHorizontal size={11} /> Filtrar por predicador
                  </span>
                  <span>{filtered.length} mensaje{filtered.length !== 1 ? "s" : ""}</span>
                </div>
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
                  {preachersList.map((preacher) => {
                    const isActive = selectedPreacher === preacher;
                    return (
                      <button
                        key={preacher}
                        type="button"
                        onClick={() => setSelectedPreacher(preacher)}
                        className={`px-3 py-1.5 rounded-full text-xs font-bold tracking-tight whitespace-nowrap transition-all border ${
                          isActive
                            ? "border-site-primary text-white shadow-2xs scale-102"
                            : "border-site-outline-variant/20 bg-site-surface-container text-site-on-surface-variant hover:bg-site-surface-container-high"
                        }`}
                        style={{
                          background: isActive ? "var(--site-primary, #2563eb)" : undefined,
                          color: isActive ? "#ffffff" : undefined,
                        }}
                      >
                        {preacher}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── CONTENIDO ── */}
      <section className="px-4 sm:px-6 md:px-8 xl:px-12 py-10 pb-24">
        <div className="max-w-7xl mx-auto">
          {/* Cargando */}
          {loading && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
              {[...Array(8)].map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          )}

          {/* Error de conexión */}
          {!loading && error && (
            <div className="text-center py-20">
              <Youtube size={52} className="mx-auto mb-4 text-site-primary/30" />
              {emptyTitle && (
                <h2 className="text-lg font-bold text-site-on-surface mb-2">{emptyTitle}</h2>
              )}
              {emptyDescription && (
                <p className="text-sm text-site-on-surface-variant mb-6 max-w-md mx-auto">{emptyDescription}</p>
              )}
              {retryLabel && (
                <button
                  onClick={load}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-white text-sm font-bold shadow-sm hover:opacity-95 transition-opacity"
                  style={{ background: "var(--site-cta-gradient, #2563eb)" }}
                >
                  <RefreshCw size={15} /> {retryLabel}
                </button>
              )}
            </div>
          )}

          {/* Sin resultados de búsqueda */}
          {!loading && !error && filtered.length === 0 && (
            <div className="text-center py-16 border border-dashed border-site-outline-variant/20 rounded-3xl p-8 max-w-md mx-auto bg-site-surface-container/30">
              <Search size={40} className="mx-auto mb-4 text-site-primary/40" />
              <h2 className="text-base font-bold text-site-on-surface mb-1">
                No encontramos prédicas que coincidan
              </h2>
              <p className="text-xs text-site-on-surface-variant mb-4">
                Prueba buscando otro término o restablece los filtros de predicador.
              </p>
              <button
                type="button"
                onClick={() => {
                  setSearch("");
                  setSelectedPreacher("Todos");
                }}
                className="text-xs font-bold text-site-primary hover:underline"
              >
                Restablecer búsqueda y filtros
              </button>
            </div>
          )}

          {/* Videos Grid */}
          {!loading && !error && filtered.length > 0 && (
            <>
              {/* Video destacado (solo sin búsqueda y con todos los predicadores) */}
              {featured && (
                <div className="mb-10">
                  <div className="flex items-center justify-between mb-4">
                    {featuredLabel && (
                      <h2
                        className="text-xs font-extrabold uppercase tracking-widest flex items-center gap-2"
                        style={{ color: "var(--site-primary, #2563eb)" }}
                      >
                        <Play size={12} fill="currentColor" /> {featuredLabel}
                      </h2>
                    )}
                    {channelLinkLabel && youtubeChannelUrl && (
                      <a
                        href={youtubeChannelUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-site-outline hover:text-site-primary transition-colors"
                      >
                        {channelLinkLabel} <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                  <VideoCard
                    video={featured}
                    featured
                    watched={Boolean(watched[featured.id])}
                    onPlay={() => openPlayer(featured)}
                    onShare={() => shareWA(featured)}
                    onCopy={() => copyLink(featured)}
                    copied={copied === featured.id}
                    featuredBadge={featuredBadge}
                    shareWhatsapp={shareWhatsapp}
                    copyLinkLabel={copyLinkLabel}
                  />
                </div>
              )}

              {/* Grid de Prédicas */}
              {rest.length > 0 && (
                <>
                  <div className="flex items-center justify-between mb-4">
                    {(search || selectedPreacher !== "Todos" ? resultsLabel : gridLabel) && (
                      <h2
                        className="text-xs font-extrabold uppercase tracking-widest"
                        style={{ color: "var(--site-primary, #2563eb)" }}
                      >
                        {search || selectedPreacher !== "Todos"
                          ? `${resultsLabel} (${filtered.length})`
                          : gridLabel}
                      </h2>
                    )}
                    {!search && selectedPreacher === "Todos" && moreVideosLabel && (
                      <span className="text-xs text-site-outline font-medium">
                        {rest.length} {moreVideosLabel}
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                    {rest.map((v) => (
                      <VideoCard
                        key={v.id}
                        video={v}
                        watched={Boolean(watched[v.id])}
                        onPlay={() => openPlayer(v)}
                        onShare={() => shareWA(v)}
                        onCopy={() => copyLink(v)}
                        copied={copied === v.id}
                        featuredBadge={featuredBadge}
                        shareWhatsapp={shareWhatsapp}
                        copyLinkLabel={copyLinkLabel}
                      />
                    ))}
                  </div>
                </>
              )}

              {/* CTA Oficial a YouTube */}
              {ctaLabel && youtubeChannelUrl && (
                <div className="mt-16 text-center">
                  <a
                    href={youtubeChannelUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2.5 px-8 py-3.5 rounded-xl text-white font-bold text-xs uppercase tracking-wider hover:scale-102 transition-all shadow-md"
                    style={{
                      background: "var(--site-cta-gradient, #2563eb)",
                      boxShadow: "var(--site-cta-shadow)",
                    }}
                  >
                    <Youtube size={18} /> {ctaLabel}
                  </a>
                </div>
              )}
            </>
          )}
        </div>
      </section>

      {/* ── DRAWER LATERAL DESLIZANTE AUTÓNOMO (REGLA MANDATORIA 0 MODALES) ── */}
      <SermonDetailDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        video={drawerVideo}
        allVideos={displayVideos}
        onSelectVideo={(newVideo) => {
          setDrawerVideo(newVideo);
          setWatched((prev) => {
            const next = { ...prev, [newVideo.id]: new Date().toISOString() };
            saveWatched(next);
            return next;
          });
        }}
        shareWhatsappLabel={shareWhatsapp}
        copyLinkLabel={copyLinkLabel}
        copiedLabel={copiedLabel}
        viewOnYoutubeLabel={viewOnYoutube}
      />
    </main>
  );
}

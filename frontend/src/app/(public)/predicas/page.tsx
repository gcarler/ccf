"use client";

import React, { useEffect, useState, useCallback, useMemo, useRef } from "react";
import OptimizedImage from "@/components/ui/OptimizedImage";
import {
    Play, Calendar, Youtube, RefreshCw, ExternalLink,
    Search, X, Check, Link2, MessageCircle, BookOpen, Eye,
} from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";
import { SITE_KEY } from "@/lib/site-config";
import CmsPageOverride from "@/components/public/cms/CmsPageOverride";
import { apiFetch } from "@/lib/http";

/* ── Tipos ── */
interface YTVideo {
    id: string;
    title: string;
    description: string;
    published_at: string;
    view_count: number;
    thumbnail_hq: string;
    thumbnail_mq: string;
    url: string;
    embed_url: string;
}
interface YTResponse {
    videos: YTVideo[];
    total: number;
    channel: string;
    error?: string;
}

/* ── Helpers ── */
function formatDate(iso: string) {
    if (!iso) return "";
    return new Date(iso).toLocaleDateString("es-CO", { day: "numeric", month: "long", year: "numeric" });
}
function timeAgo(iso: string) {
    if (!iso) return "";
    const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
    if (days === 0) return "hoy";
    if (days === 1) return "ayer";
    if (days < 7)  return `hace ${days} días`;
    if (days < 30) return `hace ${Math.floor(days / 7)} sem.`;
    if (days < 365) return `hace ${Math.floor(days / 30)} meses`;
    return `hace ${Math.floor(days / 365)} año${Math.floor(days / 365) > 1 ? "s" : ""}`;
}
function formatViews(n: number) {
    if (!n) return "";
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000)     return `${Math.round(n / 1_000)}K`;
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
const LS_KEY = "faro-predicas-watched";
function loadWatched(): Record<string, string> {
    if (typeof window === "undefined") return {};
    try { return JSON.parse(localStorage.getItem(LS_KEY) ?? "{}"); } catch { return {}; }
}
function saveWatched(w: Record<string, string>) {
    localStorage.setItem(LS_KEY, JSON.stringify(w));
}

/* ── Skeleton ── */
function SkeletonCard() {
    return (
        <div className="rounded-2xl overflow-hidden animate-pulse" style={{ background: "var(--site-surface-container)" }}>
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
    video, featured = false, watched, onPlay, onShare, onCopy, copied,
    featuredBadge, shareWhatsapp, copyLinkLabel,
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
    const [imgErr, _setImgErr] = useState(false);
    const desc = cleanDesc(video.description);

    return (
        <div
            className={`group relative rounded-2xl overflow-hidden transition-all duration-300 hover:-translate-y-1 cursor-pointer ${
                featured ? "ring-2 ring-site-primary/30" : ""
            }`}
            style={{
                background: "var(--site-surface-container)",
                boxShadow: featured ? "0 8px 40px -8px var(--site-glow-intense)" : undefined,
            }}
        >
            {/* Thumbnail — clic abre reproductor */}
            <div className="relative overflow-hidden aspect-video bg-site-surface-container-lowest" onClick={onPlay}>
                <OptimizedImage
                    src={imgErr ? video.thumbnail_mq : video.thumbnail_hq}
                    alt={video.title}
                    fill
                    sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                {/* Play button */}
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300">
                    <div className="w-16 h-16 rounded-full flex items-center justify-center backdrop-blur-sm border border-white/30 shadow-2xl" style={{ background: "var(--site-hero-bg-light)" }}>
                        <Play size={28} className="text-white ml-1" fill="white" />
                    </div>
                </div>

                {/* Badges */}
                <div className="absolute top-2.5 left-2.5 flex gap-1.5">
                    {featured && (
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-black/60 text-white text-[9px] font-bold uppercase tracking-wider backdrop-blur-sm">
                            <Youtube size={9} /> {featuredBadge}
                        </span>
                    )}
                    {watched && (
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-black/60 text-white text-[9px] font-bold uppercase tracking-wider backdrop-blur-sm">
                            <Eye size={9} /> Visto
                        </span>
                    )}
                </div>

                {/* Tiempo */}
                <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded text-[10px] font-semibold text-white backdrop-blur-md" style={{ background: "rgba(0,0,0,0.6)" }}>
                    {timeAgo(video.published_at)}
                </span>
            </div>

            {/* Info */}
            <div className={`p-4 ${featured ? "md:p-5" : ""}`}>
                <h3
                    onClick={onPlay}
                    className={`font-bold text-site-on-surface group-hover:text-site-primary transition-colors leading-snug line-clamp-2 mb-1.5 ${
                        featured ? "text-xl md:text-2xl" : "text-sm"
                    }`}
                >
                    {video.title}
                </h3>

                {featured && desc && (
                    <p className="text-sm text-site-on-surface-variant line-clamp-2 mb-3">{desc}</p>
                )}

                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5 text-[11px] text-site-outline font-medium">
                        <span className="flex items-center gap-1">
                            <Calendar size={10} /> {formatDate(video.published_at)}
                        </span>
                        {video.view_count > 0 && (
                            <span className="flex items-center gap-1">
                                <Eye size={10} /> {formatViews(video.view_count)}
                            </span>
                        )}
                    </div>

                    {/* Acciones rápidas */}
                    <div className="flex items-center gap-1 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                        <button
                            onClick={(e) => { e.stopPropagation(); onShare(); }}
                            title={shareWhatsapp}
                            className="p-1.5 rounded-lg hover:bg-site-primary/10 text-site-outline hover:text-site-on-surface transition-colors"
                        >
                            <MessageCircle size={14} />
                        </button>
                        <button
                            onClick={(e) => { e.stopPropagation(); onCopy(); }}
                            title={copyLinkLabel}
                            className="p-1.5 rounded-lg hover:bg-site-primary/10 text-site-outline hover:text-site-primary transition-colors"
                        >
                            {copied ? <Check size={14} /> : <Link2 size={14} />}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

/* ── Modal reproductor ── */
function PlayerModal({
    video, onClose, onShare, onCopy, copied,
    shareWhatsapp, copyLinkLabel, copiedLabel, viewOnYoutube,
}: {
    video: YTVideo;
    onClose: () => void;
    onShare: () => void;
    onCopy: () => void;
    copied: boolean;
    shareWhatsapp: string;
    copyLinkLabel: string;
    copiedLabel: string;
    viewOnYoutube: string;
}) {
    const desc = cleanDesc(video.description);

    /* Cerrar con Escape */
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
        document.addEventListener("keydown", onKey);
        document.body.style.overflow = "hidden";
        return () => {
            document.removeEventListener("keydown", onKey);
            document.body.style.overflow = "";
        };
    }, [onClose]);

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-8"
            style={{ background: "rgba(0,0,0,0.93)", backdropFilter: "blur(8px)" }}
            onClick={(e) => e.target === e.currentTarget && onClose()}
        >
            <div className="w-full max-w-4xl">
                {/* Cabecera */}
                <div className="flex items-start justify-between mb-3 gap-4">
                    <div className="flex-1 min-w-0">
                        <h2 className="font-bold text-white text-base md:text-xl leading-snug line-clamp-2">
                            {video.title}
                        </h2>
                        <p className="text-white/40 text-xs mt-0.5">{formatDate(video.published_at)}</p>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                        <button
                            onClick={onShare}
                            title={shareWhatsapp}
                            className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-bold text-white/70 hover:text-white hover:bg-white/10 transition-all"
                        >
                            <MessageCircle size={14} /> <span className="hidden sm:inline">{shareWhatsapp}</span>
                        </button>
                        <button
                            onClick={onCopy}
                            title={copyLinkLabel}
                            className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-bold transition-all"
                            style={{ color: copied ? "#22c55e" : "rgba(255,255,255,0.7)" }}
                        >
                            {copied
                                ? <><Check size={14} /> <span className="hidden sm:inline">{copiedLabel}</span></>
                                : <><Link2 size={14} /> <span className="hidden sm:inline">{copyLinkLabel}</span></>
                            }
                        </button>
                        <a
                            href={video.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title={viewOnYoutube}
                            className="p-2 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-all"
                        >
                            <ExternalLink size={16} />
                        </a>
                        <button
                            onClick={onClose}
                            className="p-2 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-all"
                        >
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {/* Iframe */}
                <div className="aspect-video rounded-xl overflow-hidden bg-black shadow-2xl">
                    <iframe
                        src={video.embed_url}
                        title={video.title}
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                        allowFullScreen
                        className="w-full h-full"
                    />
                </div>

                {/* Descripción limpia */}
                {desc && (
                    <p className="mt-3 text-white/40 text-xs leading-relaxed line-clamp-3 max-w-3xl">
                        {desc}
                    </p>
                )}
            </div>
        </div>
    );
}

/* ── Página principal ── */
export default function PredicasPage() {
    const { data: feedContent } = useContentBlock(`${SITE_KEY}_sermons_feed`);
    const [data, setData]     = useState<YTResponse | null>(null);
    const [loading, setLoad]  = useState(true);
    const [error, setError]   = useState(false);
    const [search, setSearch] = useState("");
    const [player, setPlayer] = useState<YTVideo | null>(null);
    const [watched, setWatched] = useState<Record<string, string>>({});
    const [copied, setCopied]   = useState<string | null>(null);
    const searchRef = useRef<HTMLInputElement>(null);

    /* Cargar historial */
    useEffect(() => { setWatched(loadWatched()); }, []);

    /* Fetch videos */
    const load = useCallback(async () => {
        setLoad(true); setError(false);
        try {
            const res = await apiFetch<YTResponse>("/youtube/videos", { silent: true });
            setData(res);
        } catch { setError(true); }
        finally { setLoad(false); }
    }, []);
    useEffect(() => { load(); }, [load]);

    const feed = feedContent?.content ? JSON.parse(feedContent.content) : null;

    const featuredBadge = feed?.featured_badge || "Más reciente";
    const retryLabel = feed?.retry_label || "Reintentar";
    const shareWhatsapp = feed?.share_whatsapp || "WhatsApp";
    const copyLinkLabel = feed?.copy_link || "Copiar";
    const copiedLabel = feed?.copied_label || "¡Copiado!";
    const viewOnYoutube = feed?.view_on_youtube || "Ver en YouTube";
    const _closeLabel = feed?.close || "Cerrar";

    /* Marcar visto + abrir reproductor */
    const openPlayer = useCallback((video: YTVideo) => {
        setPlayer(video);
        setWatched(prev => {
            const next = { ...prev, [video.id]: new Date().toISOString() };
            saveWatched(next);
            return next;
        });
    }, []);

    /* Compartir WhatsApp */
    const shareWA = useCallback((video: YTVideo) => {
        const text = encodeURIComponent(`🎙️ ${video.title}\n\n${video.url}`);
        window.open(`https://wa.me/?text=${text}`, "_blank");
    }, []);

    /* Copiar link */
    const copyLink = useCallback(async (video: YTVideo) => {
        await navigator.clipboard.writeText(video.url);
        setCopied(video.id);
        setTimeout(() => setCopied(null), 2000);
    }, []);

    /* Videos filtrados por búsqueda */
    const videos = data?.videos ?? [];
    const filtered = useMemo(() => {
        const q = search.trim().toLowerCase();
        if (!q) return videos;
        return videos.filter(v =>
            v.title.toLowerCase().includes(q) ||
            v.description.toLowerCase().includes(q)
        );
    }, [videos, search]);

    /* Conteo mensual de prédicas vistas */
    const viewedThisMonth = useMemo(() => {
        const now = new Date();
        return Object.values(watched).filter(d => {
            const dt = new Date(d);
            return dt.getMonth() === now.getMonth() && dt.getFullYear() === now.getFullYear();
        }).length;
    }, [watched]);

    const featured = !search.trim() ? (filtered[0] ?? null) : null;
    const rest     = !search.trim() ? filtered.slice(1) : filtered;

    return (
        <CmsPageOverride slug="predicas">
            <main className="min-h-screen bg-site-background pt-[88px]">

                {/* ── HERO ── */}
                <section className="relative px-4 sm:px-6 md:px-8 xl:px-12 pt-14 pb-10 overflow-hidden">
                    <div
                        className="absolute -top-32 -right-32 w-[500px] h-[500px] rounded-full blur-3xl pointer-events-none"
                        style={{ background: "radial-gradient(ellipse, var(--site-glow-subtle) 0%, transparent 70%)" }}
                    />
                    <div className="max-w-7xl mx-auto">
                        <div className="flex items-center gap-3 mb-4">
                            <span className="w-8 h-0.5 bg-site-primary" />
                            <span className="text-[11px] font-bold uppercase tracking-widest text-site-primary flex items-center gap-2">
                                <Youtube size={13} /> {feed?.hero_eyebrow || "Ministerios Faro Oficial"}
                            </span>
                        </div>

                        <h1
                            className="max-w-4xl font-black tracking-tight text-site-on-surface leading-[0.92] mb-3 text-4xl sm:text-5xl lg:text-6xl"
                        >
                            {feed?.hero_title_lead || "Prédicas &"} <br />
                            <span className="italic" style={{ background: "var(--site-hero-cta-gradient)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                                {feed?.hero_title_accent || "Mensajes"}
                            </span>
                        </h1>

                        <p className="text-base sm:text-lg text-site-on-surface-variant max-w-xl leading-relaxed mb-4">
                            {feed?.hero_description || "Alimento para el alma — explora los mensajes más recientes de nuestro canal de YouTube."}
                        </p>

                        {/* Contador de vistas del mes */}
                        {viewedThisMonth > 0 && (
                            <div className="inline-flex items-center gap-2 text-xs font-semibold text-site-primary mb-2">
                                <BookOpen size={13} />
                                {viewedThisMonth} mensaje{viewedThisMonth !== 1 ? "s" : ""} {feed?.watched_label || "visto"}{viewedThisMonth !== 1 ? "s" : ""} este mes
                            </div>
                        )}

                        {/* Buscador */}
                        <div className="relative max-w-md mt-2">
                            <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-site-outline pointer-events-none" />
                            <input
                                ref={searchRef}
                                type="text"
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                placeholder={feed?.search_placeholder || "Buscar por título o predicador…"}
                                className="w-full rounded-xl pl-10 pr-9 py-2.5 text-sm text-site-on-surface placeholder:text-site-outline outline-none focus:ring-2 focus:ring-site-primary/30 transition-all"
                                style={{ background: "var(--site-surface-container)", border: "1px solid var(--site-outline-variant)" }}
                            />
                            {search && (
                                <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-site-outline hover:text-site-on-surface transition-colors">
                                    <X size={14} />
                                </button>
                            )}
                        </div>
                    </div>
                </section>

                {/* ── CONTENIDO ── */}
                <section className="px-4 sm:px-6 md:px-8 xl:px-12 pb-24">
                    <div className="max-w-7xl mx-auto">

                        {/* Cargando */}
                        {loading && (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                                {[...Array(6)].map((_, i) => <SkeletonCard key={i} />)}
                            </div>
                        )}

                        {/* Error */}
                        {!loading && error && (
                            <div className="text-center py-20">
                                <Youtube size={52} className="mx-auto mb-4 text-site-primary/30" />
                                <h2 className="text-lg font-bold text-site-on-surface mb-2">{feed?.empty_title || "No se pudieron cargar los videos"}</h2>
                                <p className="text-sm text-site-on-surface-variant mb-6">{feed?.empty_description || "Verifica tu conexión o intenta nuevamente."}</p>
                                <button onClick={load} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-white text-sm font-bold" style={{ background: "var(--site-cta-gradient)" }}>
                                    <RefreshCw size={15} /> {retryLabel}
                                </button>
                            </div>
                        )}

                        {/* Sin resultados de búsqueda */}
                        {!loading && !error && filtered.length === 0 && search && (
                            <div className="text-center py-16">
                                <Search size={40} className="mx-auto mb-4 text-site-primary/30" />
                                <h2 className="text-base font-bold text-site-on-surface mb-1">Sin resultados para &quot;{search}&quot;</h2>
                                <p className="text-sm text-site-on-surface-variant">Intenta con otro término.</p>
                            </div>
                        )}

                        {/* Videos */}
                        {!loading && !error && filtered.length > 0 && (
                            <>
                                {/* Video destacado (solo sin búsqueda activa) */}
                                {featured && (
                                    <div className="mb-8">
                                        <div className="flex items-center justify-between mb-4">
                                            <h2 className="text-sm font-bold uppercase tracking-widest text-site-primary">{feed?.featured_label || "Último mensaje"}</h2>
                                            <a href="https://www.youtube.com/@Ministeriosfarooficial" target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-site-outline hover:text-site-primary transition-colors">
                                                {feed?.channel_link_label || "Ver canal"} <ExternalLink size={11} />
                                            </a>
                                        </div>
                                        <VideoCard
                                            video={featured}
                                            featured
                                            watched={!!watched[featured.id]}
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

                                {/* Grid */}
                                {rest.length > 0 && (
                                    <>
                                        <div className="flex items-center justify-between mb-4">
                                            <h2 className="text-sm font-bold uppercase tracking-widest text-site-primary">
                                                {search ? `${feed?.results_label || "Resultados"} (${filtered.length})` : (feed?.grid_label || "Más mensajes")}
                                            </h2>
                                            {!search && (
                                                <span className="text-[11px] text-site-outline">{rest.length} {feed?.more_videos_label || "videos"}</span>
                                            )}
                                        </div>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                                            {rest.map(v => (
                                                <VideoCard
                                                    key={v.id}
                                                    video={v}
                                                    watched={!!watched[v.id]}
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

                                {/* CTA */}
                                <div className="mt-14 text-center">
                                    <a
                                        href="https://www.youtube.com/@Ministeriosfarooficial"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-2.5 px-7 py-3.5 rounded-xl text-white font-bold text-sm uppercase tracking-wider hover:scale-105 transition-all"
                                        style={{ background: "var(--site-cta-gradient)", boxShadow: "var(--site-cta-shadow)" }}
                                    >
                                        <Youtube size={18} /> {feed?.cta_label || "Ver todos en YouTube"}
                                    </a>
                                </div>
                            </>
                        )}
                    </div>
                </section>

                {/* ── REPRODUCTOR MODAL ── */}
                {player && (
                    <PlayerModal
                        video={player}
                        onClose={() => setPlayer(null)}
                        onShare={() => shareWA(player)}
                        onCopy={() => copyLink(player)}
                        copied={copied === player.id}
                        shareWhatsapp={shareWhatsapp}
                        copyLinkLabel={copyLinkLabel}
                        copiedLabel={copiedLabel}
                        viewOnYoutube={viewOnYoutube}
                    />
                )}
            </main>
        </CmsPageOverride>
    );
}

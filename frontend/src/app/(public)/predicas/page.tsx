"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Play, Calendar, Eye, Loader2, Youtube, RefreshCw, ExternalLink } from "lucide-react";
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
function formatDate(iso: string): string {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("es-CO", { day: "numeric", month: "long", year: "numeric" });
}

function formatViews(n: number): string {
    if (!n) return "";
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M vistas`;
    if (n >= 1_000)     return `${Math.round(n / 1_000)}K vistas`;
    return `${n} vistas`;
}

function timeAgo(iso: string): string {
    if (!iso) return "";
    const diff = Date.now() - new Date(iso).getTime();
    const days = Math.floor(diff / 86_400_000);
    if (days === 0) return "hoy";
    if (days === 1) return "ayer";
    if (days < 7)  return `hace ${days} días`;
    if (days < 30) return `hace ${Math.floor(days / 7)} sem.`;
    if (days < 365) return `hace ${Math.floor(days / 30)} meses`;
    return `hace ${Math.floor(days / 365)} año${Math.floor(days / 365) > 1 ? "s" : ""}`;
}

/* ── Skeleton card ── */
function SkeletonCard({ large = false }: { large?: boolean }) {
    return (
        <div
            className={`rounded-2xl overflow-hidden animate-pulse ${large ? "col-span-full md:col-span-2" : ""}`}
            style={{ background: "var(--faro-surface-container)" }}
        >
            <div className={`bg-faro-outline-variant/20 ${large ? "aspect-video" : "aspect-video"}`} />
            <div className="p-4 space-y-2">
                <div className="h-4 bg-faro-outline-variant/20 rounded w-3/4" />
                <div className="h-3 bg-faro-outline-variant/10 rounded w-1/2" />
            </div>
        </div>
    );
}

/* ── Card de video ── */
function VideoCard({ video, featured = false }: { video: YTVideo; featured?: boolean }) {
    const [imgError, setImgError] = useState(false);

    return (
        <a
            href={video.url}
            target="_blank"
            rel="noopener noreferrer"
            className={`group block rounded-2xl overflow-hidden transition-all duration-300 hover:-translate-y-1 ${
                featured
                    ? "col-span-full md:col-span-2 ring-2 ring-faro-primary/30"
                    : ""
            }`}
            style={{
                background: "var(--faro-surface-container)",
                boxShadow: featured ? "0 8px 40px -8px var(--faro-glow-intense)" : undefined,
            }}
        >
            {/* Thumbnail */}
            <div className="relative overflow-hidden aspect-video bg-faro-surface-container-lowest">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                    src={imgError ? video.thumbnail_mq : video.thumbnail_hq}
                    alt={video.title}
                    onError={() => setImgError(true)}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                />

                {/* Overlay gradiente */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

                {/* Botón play */}
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300">
                    <div
                        className="w-16 h-16 rounded-full flex items-center justify-center backdrop-blur-sm border border-white/30 shadow-2xl"
                        style={{ background: "var(--faro-hero-bg-light)" }}
                    >
                        <Play size={28} className="text-white ml-1" fill="white" />
                    </div>
                </div>

                {/* Badge YouTube */}
                {featured && (
                    <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#FF0000] text-white text-[10px] font-bold uppercase tracking-wider">
                        <Youtube size={10} /> Más reciente
                    </div>
                )}

                {/* Fecha flotante */}
                <div
                    className="absolute bottom-2 right-2 px-2 py-0.5 rounded text-[10px] font-semibold text-white backdrop-blur-md"
                    style={{ background: "rgba(0,0,0,0.6)" }}
                >
                    {timeAgo(video.published_at)}
                </div>
            </div>

            {/* Info */}
            <div className={`p-4 ${featured ? "md:p-5" : ""}`}>
                <h3
                    className={`font-bold text-faro-on-surface group-hover:text-faro-primary transition-colors leading-snug line-clamp-2 ${
                        featured ? "text-xl md:text-2xl mb-2" : "text-sm mb-1.5"
                    }`}
                >
                    {video.title}
                </h3>

                {featured && video.description && (
                    <p className="text-sm text-faro-on-surface-variant line-clamp-2 mb-3">
                        {video.description}
                    </p>
                )}

                <div className="flex items-center gap-3 text-[11px] text-faro-outline font-medium">
                    <span className="flex items-center gap-1">
                        <Calendar size={11} /> {formatDate(video.published_at)}
                    </span>
                    {video.view_count > 0 && (
                        <span className="flex items-center gap-1">
                            <Eye size={11} /> {formatViews(video.view_count)}
                        </span>
                    )}
                </div>
            </div>
        </a>
    );
}

/* ── Página principal ── */
export default function PredicasPage() {
    const [data, setData]       = useState<YTResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError]     = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        setError(false);
        try {
            const res = await apiFetch<YTResponse>("/youtube/videos", { silent: true });
            setData(res);
        } catch {
            setError(true);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const videos   = data?.videos ?? [];
    const featured = videos[0] ?? null;
    const rest     = videos.slice(1);

    return (
        <CmsPageOverride slug="predicas">
            <main className="min-h-screen bg-faro-background pt-[88px]">

                {/* ── HERO ── */}
                <section className="relative px-4 sm:px-6 md:px-8 xl:px-12 pt-14 pb-10 overflow-hidden">
                    {/* Glow de fondo */}
                    <div
                        className="absolute -top-32 -right-32 w-[500px] h-[500px] rounded-full blur-3xl pointer-events-none"
                        style={{ background: "radial-gradient(ellipse, var(--faro-glow-subtle) 0%, transparent 70%)" }}
                    />

                    <div className="max-w-7xl mx-auto">
                        {/* Eyebrow */}
                        <div className="flex items-center gap-3 mb-4">
                            <span className="w-8 h-0.5 bg-faro-primary" />
                            <span className="text-[11px] font-bold uppercase tracking-widest text-faro-primary flex items-center gap-2">
                                <Youtube size={13} /> Ministerios Faro Oficial
                            </span>
                        </div>

                        {/* Título */}
                        <h1
                            className="font-black tracking-tight text-faro-on-surface leading-[0.92] mb-4"
                            style={{ fontSize: "clamp(2.8rem, 6vw, 5.5rem)" }}
                        >
                            Prédicas &amp; <br />
                            <span
                                className="italic"
                                style={{
                                    background: "var(--faro-hero-cta-gradient)",
                                    WebkitBackgroundClip: "text",
                                    WebkitTextFillColor: "transparent",
                                }}
                            >
                                Mensajes
                            </span>
                        </h1>
                        <p className="text-base md:text-lg text-faro-on-surface-variant max-w-xl leading-relaxed">
                            Alimento para el alma — explora los mensajes más recientes de nuestro canal de YouTube.
                        </p>
                    </div>
                </section>

                {/* ── CONTENIDO ── */}
                <section className="px-4 sm:px-6 md:px-8 xl:px-12 pb-20">
                    <div className="max-w-7xl mx-auto">

                        {/* Estado: cargando */}
                        {loading && (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                                <SkeletonCard large />
                                {[...Array(5)].map((_, i) => <SkeletonCard key={i} />)}
                            </div>
                        )}

                        {/* Estado: error */}
                        {!loading && error && (
                            <div className="text-center py-20">
                                <Youtube size={56} className="mx-auto mb-4 text-faro-primary/30" />
                                <h2 className="text-lg font-bold text-faro-on-surface mb-2">
                                    No se pudieron cargar los videos
                                </h2>
                                <p className="text-sm text-faro-on-surface-variant mb-6">
                                    Verifica tu conexión o intenta nuevamente.
                                </p>
                                <button
                                    onClick={load}
                                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-faro-on-primary text-sm font-bold"
                                    style={{ background: "var(--faro-cta-gradient)" }}
                                >
                                    <RefreshCw size={15} /> Reintentar
                                </button>
                            </div>
                        )}

                        {/* Estado: sin videos */}
                        {!loading && !error && videos.length === 0 && (
                            <div className="text-center py-20">
                                <Youtube size={56} className="mx-auto mb-4 text-faro-primary/30" />
                                <h2 className="text-lg font-bold text-faro-on-surface mb-2">Sin videos disponibles</h2>
                                <p className="text-sm text-faro-on-surface-variant">
                                    El canal aún no tiene videos públicos o el feed no está disponible.
                                </p>
                            </div>
                        )}

                        {/* Estado: videos cargados */}
                        {!loading && !error && videos.length > 0 && (
                            <>
                                {/* Video destacado */}
                                {featured && (
                                    <div className="mb-8">
                                        <div className="flex items-center justify-between mb-4">
                                            <h2 className="text-sm font-bold uppercase tracking-widest text-faro-primary">
                                                Último mensaje
                                            </h2>
                                            <a
                                                href={`https://www.youtube.com/${data?.channel}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-faro-outline hover:text-faro-primary transition-colors"
                                            >
                                                Ver canal <ExternalLink size={11} />
                                            </a>
                                        </div>
                                        <VideoCard video={featured} featured />
                                    </div>
                                )}

                                {/* Grid de videos */}
                                {rest.length > 0 && (
                                    <>
                                        <div className="flex items-center justify-between mb-4">
                                            <h2 className="text-sm font-bold uppercase tracking-widest text-faro-primary">
                                                Más mensajes
                                            </h2>
                                            <span className="text-[11px] text-faro-outline">
                                                {rest.length} video{rest.length !== 1 ? "s" : ""}
                                            </span>
                                        </div>
                                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                                            {rest.map((v) => (
                                                <VideoCard key={v.id} video={v} />
                                            ))}
                                        </div>
                                    </>
                                )}

                                {/* Footer CTA */}
                                <div className="mt-14 text-center">
                                    <a
                                        href="https://www.youtube.com/@Ministeriosfarooficial"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-2.5 px-7 py-3.5 rounded-xl text-white font-bold text-sm uppercase tracking-wider hover:scale-105 transition-all"
                                        style={{ background: "var(--faro-cta-gradient)", boxShadow: "var(--faro-cta-shadow)" }}
                                    >
                                        <Youtube size={18} /> Ver todos en YouTube
                                    </a>
                                </div>
                            </>
                        )}
                    </div>
                </section>

            </main>
        </CmsPageOverride>
    );
}

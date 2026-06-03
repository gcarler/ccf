"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  ExternalLink,
  FileText,
  Globe,
  ImageIcon,
  Layers3,
  Link2,
  LucideIcon,
  Megaphone,
  MessageCircle,
  Palette,
  PanelsTopLeft,
  ShieldCheck,
  Video,
  Volume2,
} from "lucide-react";
import AdminHero from "@/components/admin/AdminHero";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { FARO_BLOCKS } from "@/lib/cms/blocks";
import { canEditCms, canManageSites } from "@/lib/cms/permissions";

interface CmsStats {
  testimonials: number;
  pendingTestimonials: number;
  approvedTestimonials: number;
  sections: number;
  publishedBlocks: number;
  inReviewBlocks: number;
  activeAnnouncements: number;
  mediaTotal: number;
  mediaImages: number;
  mediaVideos: number;
  mediaAudio: number;
  mediaWithoutAlt: number;
}

interface TestimonialPreview {
  id: number;
  content: string;
  emotion: string;
  created_at: string;
  is_approved?: boolean;
  status?: string;
}

interface MediaPreview {
  id: number;
  alt_text?: string | null;
  filename?: string | null;
  mime_type?: string | null;
  status?: string | null;
}

interface CmsMetricsResponse {
  published_blocks: number;
  in_review_blocks: number;
  announcements_active: number;
  testimonials_approved: number;
  media_total: number;
  media_images: number;
  media_videos: number;
  media_audio: number;
}

type QualityTone = "success" | "warning";

type QualityCheck = {
  label: string;
  description: string;
  value: number;
  href: string;
  tone: QualityTone;
  icon: LucideIcon;
};

const EMPTY_STATS: CmsStats = {
  testimonials: 0,
  pendingTestimonials: 0,
  approvedTestimonials: 0,
  sections: FARO_BLOCKS.length,
  publishedBlocks: 0,
  inReviewBlocks: 0,
  activeAnnouncements: 0,
  mediaTotal: 0,
  mediaImages: 0,
  mediaVideos: 0,
  mediaAudio: 0,
  mediaWithoutAlt: 0,
};

function formatDate(value?: string) {
  if (!value) return "Sin fecha";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sin fecha";
  return date.toLocaleDateString("es-CO", { day: "2-digit", month: "short", year: "numeric" });
}

function metricValue(value: number | undefined, loading: boolean) {
  if (loading) return "...";
  return value ?? 0;
}

export default function CmsHomePage() {
  const { token, isAuthenticated, user } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<CmsStats>(EMPTY_STATS);
  const [recentTestimonials, setRecentTestimonials] = useState<TestimonialPreview[]>([]);
  const [loading, setLoading] = useState(true);
  const [dataIssue, setDataIssue] = useState<string | null>(null);
  const canEdit = canEditCms(user?.role);
  const canManage = canManageSites(user?.role);

  useEffect(() => {
    const fetchData = async () => {
      if (!token) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setDataIssue(null);

      const [testimonialsResult, metricsResult, mediaResult] = await Promise.allSettled([
        apiFetch<TestimonialPreview[]>("/admin/testimonials", { token, cache: "no-store" }),
        apiFetch<CmsMetricsResponse>("/cms/metrics", { token, cache: "no-store" }),
        apiFetch<MediaPreview[]>("/cms/media", { token, cache: "no-store", query: { include_archived: true } }),
      ]);

      const loadIssues: string[] = [];
      const testimonials = testimonialsResult.status === "fulfilled" && Array.isArray(testimonialsResult.value)
        ? testimonialsResult.value
        : [];
      const metrics = metricsResult.status === "fulfilled" ? metricsResult.value : null;
      const media = mediaResult.status === "fulfilled" && Array.isArray(mediaResult.value)
        ? mediaResult.value
        : [];

      if (testimonialsResult.status === "rejected") loadIssues.push("testimonios");
      if (metricsResult.status === "rejected") loadIssues.push("metricas");
      if (mediaResult.status === "rejected") loadIssues.push("media");

      const visibleMedia = media.filter((item) => item.status !== "archived");
      const missingAlt = visibleMedia.filter(
        (item) => (item.mime_type || "").startsWith("image/") && !String(item.alt_text || "").trim(),
      ).length;

      setRecentTestimonials(testimonials.slice(0, 5));
      setStats({
        testimonials: testimonials.length,
        pendingTestimonials: testimonials.filter((testimony) => !testimony.is_approved && testimony.status !== "archived").length,
        approvedTestimonials: metrics?.testimonials_approved ?? testimonials.filter((testimony) => testimony.is_approved).length,
        sections: FARO_BLOCKS.length,
        publishedBlocks: metrics?.published_blocks ?? 0,
        inReviewBlocks: metrics?.in_review_blocks ?? 0,
        activeAnnouncements: metrics?.announcements_active ?? 0,
        mediaTotal: metrics?.media_total ?? visibleMedia.length,
        mediaImages: metrics?.media_images ?? visibleMedia.filter((item) => (item.mime_type || "").startsWith("image/")).length,
        mediaVideos: metrics?.media_videos ?? visibleMedia.filter((item) => (item.mime_type || "").startsWith("video/")).length,
        mediaAudio: metrics?.media_audio ?? visibleMedia.filter((item) => (item.mime_type || "").startsWith("audio/")).length,
        mediaWithoutAlt: missingAlt,
      });
      setDataIssue(loadIssues.length ? `No se pudieron cargar: ${loadIssues.join(", ")}.` : null);
      setLoading(false);
    };

    fetchData().catch((error) => {
      console.error("CMS home fetch", error);
      setDataIssue("No se pudo cargar el resumen del CMS.");
      setRecentTestimonials([]);
      setStats(EMPTY_STATS);
      setLoading(false);
    });
  }, [token]);

  const quickLinks = useMemo(
    () => [
      { label: "Paginas", href: "/cms/pages", description: "Contenido, SEO y estados", icon: FileText, show: canEdit },
      { label: "Menus", href: "/cms/menus", description: "Navegacion publica", icon: Link2, show: canEdit },
      { label: "Testimonios", href: "/cms/testimonials", description: "Aprobacion y portada", icon: MessageCircle, show: canEdit },
      { label: "Builder", href: "/cms/builder", description: "Secciones visuales", icon: PanelsTopLeft, show: canEdit },
      { label: "Media", href: "/cms/media", description: "Archivos y accesibilidad", icon: ImageIcon, show: canEdit },
      { label: "Temas", href: "/cms/themes", description: "Tokens por sitio", icon: Palette, show: canEdit },
      { label: "Sitios", href: "/cms/sites", description: "Portales y dominios", icon: Globe, show: canManage },
    ].filter((link) => link.show),
    [canEdit, canManage],
  );

  const qualityChecks: QualityCheck[] = useMemo(
    () => [
      {
        label: "Testimonios pendientes",
        description: stats.pendingTestimonials > 0 ? "Historias esperando revision editorial" : "Cola de testimonios limpia",
        value: stats.pendingTestimonials,
        href: "/cms/testimonials",
        tone: stats.pendingTestimonials > 0 ? "warning" : "success",
        icon: MessageCircle,
      },
      {
        label: "Bloques en revision",
        description: stats.inReviewBlocks > 0 ? "Contenido listo para aprobar o devolver" : "Sin bloque esperando aprobacion",
        value: stats.inReviewBlocks,
        href: "/cms/content",
        tone: stats.inReviewBlocks > 0 ? "warning" : "success",
        icon: Clock3,
      },
      {
        label: "Imagenes sin alt",
        description: stats.mediaWithoutAlt > 0 ? "Completa metadata accesible en media" : "Imagenes activas con texto alternativo",
        value: stats.mediaWithoutAlt,
        href: "/cms/media",
        tone: stats.mediaWithoutAlt > 0 ? "warning" : "success",
        icon: ImageIcon,
      },
      {
        label: "Bloques publicados",
        description: stats.publishedBlocks > 0 ? "Contenido visible para el sitio" : "Aun no hay bloques publicados",
        value: stats.publishedBlocks,
        href: "/cms/content",
        tone: stats.publishedBlocks > 0 ? "success" : "warning",
        icon: Layers3,
      },
    ],
    [stats],
  );

  const qualityScore = useMemo(() => {
    if (loading) return null;
    const passed = qualityChecks.filter((check) => check.tone === "success").length;
    return Math.round((passed / qualityChecks.length) * 100);
  }, [loading, qualityChecks]);

  const metricCards = [
    { label: "Testimonios publicados", value: stats.approvedTestimonials, icon: MessageCircle },
    { label: "Pendientes", value: stats.pendingTestimonials, icon: AlertCircle },
    { label: "Media total", value: stats.mediaTotal, icon: ImageIcon },
    { label: "Imagenes", value: stats.mediaImages, icon: ImageIcon },
    { label: "Videos", value: stats.mediaVideos, icon: Video },
    { label: "Podcasts", value: stats.mediaAudio, icon: Volume2 },
    { label: "Bloques FARO", value: stats.sections, icon: Layers3 },
    { label: "Publicados", value: stats.publishedBlocks, icon: CheckCircle2 },
    { label: "En revision", value: stats.inReviewBlocks, icon: Clock3 },
    { label: "Anuncios activos", value: stats.activeAnnouncements, icon: Megaphone },
  ];

  if (!isAuthenticated) {
    return (
      <div className="h-full overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-1.5 text-center">
          <h1 className="text-xl font-semibold">Inicia sesion</h1>
          <p className="mt-3 text-slate-500">Necesitas una sesion valida para administrar el CMS.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-slate-50/60 dark:bg-[#141517]">
      <div className="space-y-3 px-4 py-2 lg:px-3">
        <AdminHero
          eyebrow="CMS"
          title="Administracion del sitio web"
          description="Control editorial para paginas, bloques, media, testimonios, eventos y publicacion multisitio."
          tags={["Calidad web", "Publicacion", "FARO"]}
          watchers={["Comunicaciones", "Pastoral", "Web"]}
          primaryAction={{ label: "Abrir sitio", icon: ExternalLink, onClick: () => window.open("/", "_blank") }}
          secondaryAction={canEdit ? { label: "Ir al builder", icon: PanelsTopLeft, onClick: () => router.push("/cms/builder") } : undefined}
        />

        {dataIssue && (
          <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{dataIssue}</span>
          </div>
        )}

        <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {metricCards.map((metric) => {
            const Icon = metric.icon;
            return (
              <div key={metric.label} className="rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-4 shadow-sm dark:border-white/10 dark:bg-[#111418]">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{metric.label}</p>
                  <Icon size={15} className="text-slate-400" />
                </div>
                <p className="mt-3 text-lg font-semibold text-slate-900 dark:text-white">
                  {metricValue(metric.value, loading)}
                </p>
              </div>
            );
          })}
        </section>

        <section className="grid grid-cols-1 gap-3 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[#111418]">
            <div className="flex flex-col gap-3 border-b border-slate-100 pb-4 dark:border-white/10 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Control de calidad</p>
                <h2 className="mt-1 text-xl font-semibold text-slate-900 dark:text-white">Prioridades editoriales</h2>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-14 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-sm font-semibold text-slate-900 dark:border-white/10 dark:bg-white/5 dark:text-white">
                  {qualityScore === null ? "..." : `${qualityScore}%`}
                </div>
                <p className="max-w-44 text-xs leading-relaxed text-slate-500">
                  Puntaje calculado desde colas pendientes, publicacion y metadata de media.
                </p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              {qualityChecks.map((check) => {
                const Icon = check.icon;
                const isWarning = check.tone === "warning";
                return (
                  <Link
                    key={check.label}
                    href={canEdit ? check.href : "/cms"}
                    className="group rounded-lg border border-slate-200 p-4 transition-colors hover:border-blue-300 dark:border-white/10 dark:hover:border-blue-500/50"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className={isWarning ? "rounded-lg bg-amber-50 p-2 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300" : "rounded-lg bg-emerald-50 p-2 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300"}>
                          <Icon size={16} />
                        </div>
                        <div>
                          <p className="text-sm font-bold text-slate-900 dark:text-white">{check.label}</p>
                          <p className="mt-1 text-xs text-slate-500">{check.description}</p>
                        </div>
                      </div>
                      <span className={isWarning ? "text-lg font-semibold text-amber-700 dark:text-amber-300" : "text-lg font-semibold text-emerald-700 dark:text-emerald-300"}>
                        {loading ? "..." : check.value}
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[#111418]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Acceso</p>
                <h2 className="mt-1 text-xl font-semibold text-slate-900 dark:text-white">Rol editorial</h2>
              </div>
              <ShieldCheck className="h-5 w-5 text-[hsl(var(--primary))]" />
            </div>
            <p className="mt-3 text-sm leading-relaxed text-slate-500">
              {canManage
                ? "Puedes administrar sitios, contenido, temas y publicacion."
                : canEdit
                  ? "Puedes editar contenido, media, eventos y flujos editoriales."
                  : "Tienes acceso de lectura al resumen. Solicita un rol editorial para modificar contenido."}
            </p>

            <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {quickLinks.map(({ label, href, description, icon: Icon }) => (
                <Link key={href} href={href} className="rounded-lg border border-slate-200 p-3 transition-colors hover:border-blue-300 dark:border-white/10 dark:hover:border-blue-500/50">
                  <div className="flex items-center gap-2">
                    <Icon size={15} className="text-[hsl(var(--primary))]" />
                    <p className="text-sm font-bold text-slate-900 dark:text-white">{label}</p>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{description}</p>
                </Link>
              ))}
              {quickLinks.length === 0 && (
                <div className="rounded-lg border border-dashed border-slate-200 p-4 text-sm text-slate-500 dark:border-white/10">
                  No hay modulos de edicion disponibles para tu rol actual.
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <div className="rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[#111418]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Testimonios recientes</h2>
                <p className="mt-1 text-sm text-slate-500">Ultimas historias recibidas para revision y publicacion.</p>
              </div>
              {canEdit && (
                <Link href="/cms/testimonials" className="rounded-lg border border-slate-200 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-600 hover:border-blue-300 hover:text-[hsl(var(--primary))] dark:border-white/10 dark:text-slate-300">
                  Ver todo
                </Link>
              )}
            </div>

            <div className="mt-4 space-y-3">
              {loading ? (
                <p className="text-sm text-slate-500">Cargando historias...</p>
              ) : recentTestimonials.length === 0 ? (
                <p className="rounded-lg border border-dashed border-slate-200 p-4 text-sm text-slate-500 dark:border-white/10">
                  Sin testimonios en la cola.
                </p>
              ) : (
                recentTestimonials.map((testimony) => (
                  <div key={testimony.id} className="rounded-lg border border-slate-200 p-4 dark:border-white/10">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{testimony.emotion || "Sin categoria"}</p>
                      <span className={testimony.is_approved ? "rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300" : "rounded-full bg-amber-50 px-2 py-1 text-[10px] font-bold text-amber-700 dark:bg-amber-500/10 dark:text-amber-300"}>
                        {testimony.is_approved ? "Aprobado" : "Pendiente"}
                      </span>
                    </div>
                    <p className="mt-2 line-clamp-2 text-sm text-slate-600 dark:text-slate-200">{testimony.content}</p>
                    <p className="mt-3 text-[11px] text-slate-400">{formatDate(testimony.created_at)}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[#111418]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Ruta de gestion</h2>
                <p className="mt-1 text-sm text-slate-500">Secuencia recomendada para publicar cambios del sitio.</p>
              </div>
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            </div>
            <div className="mt-5 space-y-3">
              {[
                { label: "Editar estructura", detail: "Paginas, menus y secciones del builder.", href: "/cms/pages" },
                { label: "Completar media", detail: "Alt text, etiquetas y archivos reutilizables.", href: "/cms/media" },
                { label: "Revisar contenido", detail: "Testimonios, bloques en revision y eventos.", href: "/cms/content" },
                { label: "Publicar", detail: "Aprobar, publicar y revisar el sitio en vivo.", href: "/" },
              ].map((step, index) => (
                <Link
                  key={step.label}
                  href={step.href}
                  className="flex items-start gap-3 rounded-lg border border-slate-200 p-3 transition-colors hover:border-blue-300 dark:border-white/10 dark:hover:border-blue-500/50"
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-xs font-semibold text-white dark:bg-[hsl(var(--bg-primary))] dark:text-slate-900">
                    {index + 1}
                  </span>
                  <span>
                    <span className="block text-sm font-bold text-slate-900 dark:text-white">{step.label}</span>
                    <span className="mt-1 block text-xs text-slate-500">{step.detail}</span>
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}


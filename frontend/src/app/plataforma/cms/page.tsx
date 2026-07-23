"use client";

import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import Link from "next/link";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Clock3,
  ExternalLink,
  Eye,
  FileText,
  Gauge,
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
  Tag,
  TrendingUp,
  Users,
  Video,
  Volume2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { SITE_BLOCKS } from "@/lib/cms/blocks";
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
  pageViewsTotal: number;
  pageViews7d: number;
  pageViews30d: number;
  postsTotal: number;
  postsPublished: number;
  categoriesTotal: number;
  tagsTotal: number;
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

interface DashboardTopPage {
  slug: string;
  title: string;
  views: number;
}

interface DashboardRecentPost {
  slug: string;
  title: string;
  published_at: string;
  status: string;
  category_count: number;
  tag_count: number;
}

interface DashboardActivity {
  entity_type: string;
  action: string;
  from_status: string | null;
  to_status: string | null;
  created_at: string;
  actor: string;
  metadata: Record<string, unknown>;
}

interface CmsDashboardResponse {
  cards: Array<{ title: string; value: string; trend?: string; tone?: string; icon?: string }>;
  page_views_total: number;
  page_views_7d: number;
  page_views_30d: number;
  top_pages: DashboardTopPage[];
  recent_posts: DashboardRecentPost[];
  recent_activity: DashboardActivity[];
  posts_total: number;
  posts_published: number;
  categories_total: number;
  tags_total: number;
  publicaciones_por_mes: Array<{ label: string; value: number }>;
  contenido_por_tipo: Array<{ label: string; value: number }>;
  borradores_pendientes: number;
  last_updated?: string;
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
  sections: SITE_BLOCKS.length,
  publishedBlocks: 0,
  inReviewBlocks: 0,
  activeAnnouncements: 0,
  mediaTotal: 0,
  mediaImages: 0,
  mediaVideos: 0,
  mediaAudio: 0,
  mediaWithoutAlt: 0,
  pageViewsTotal: 0,
  pageViews7d: 0,
  pageViews30d: 0,
  postsTotal: 0,
  postsPublished: 0,
  categoriesTotal: 0,
  tagsTotal: 0,
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

function activityLabel(activity: DashboardActivity): string {
  const entityMap: Record<string, string> = {
    page: "Página",
    post: "Post",
    section: "Sección",
    media: "Media",
    theme: "Tema",
    menu: "Menú",
  };
  const actionMap: Record<string, string> = {
    publish: "publicó",
    update: "actualizó",
    create: "creó",
    delete: "eliminó",
    rollback: "revirtió",
  };
  const entity = entityMap[activity.entity_type] || activity.entity_type;
  const action = actionMap[activity.action] || activity.action;
  return `${activity.actor} ${action} ${entity.toLowerCase()}`;
}

export default function CmsHomePage() {
  const { token, isAuthenticated, user } = useAuth();
  const [stats, setStats] = useState<CmsStats>(EMPTY_STATS);
  const [recentTestimonials, setRecentTestimonials] = useState<TestimonialPreview[]>([]);
  const [topPages, setTopPages] = useState<DashboardTopPage[]>([]);
  const [recentPosts, setRecentPosts] = useState<DashboardRecentPost[]>([]);
  const [recentActivity, setRecentActivity] = useState<DashboardActivity[]>([]);
  const [pubsChart, setPubsChart] = useState<Array<{ label: string; value: number }>>([]);
  const [contentTypeChart, setContentTypeChart] = useState<Array<{ label: string; value: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [dataIssue, setDataIssue] = useState<string | null>(null);
  const canEdit = canEditCms(user?.role);
  const canManage = canManageSites(user?.role);

  useEffect(() => {
    const fetchData = async () => {
      if (!token || !canEdit) {
        setRecentTestimonials([]);
        setTopPages([]);
        setRecentPosts([]);
        setRecentActivity([]);
        setPubsChart([]);
        setContentTypeChart([]);
        setStats(EMPTY_STATS);
        setDataIssue(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      setDataIssue(null);

      const [testimonialsResult, metricsResult, mediaResult, dashboardResult] = await Promise.allSettled([
        apiFetch<TestimonialPreview[]>("/admin/testimonials", { token, cache: "no-store" }),
        apiFetch<CmsMetricsResponse>("/cms/metrics", { token, cache: "no-store" }),
        apiFetch<{ items: MediaPreview[]; total: number }>("/cms/media", { token, cache: "no-store", query: { include_archived: true } }),
        apiFetch<CmsDashboardResponse>("/dashboard/cms", { token, cache: "no-store" }),
      ]);

      const loadIssues: string[] = [];
      const testimonials = testimonialsResult.status === "fulfilled" && Array.isArray(testimonialsResult.value)
        ? testimonialsResult.value
        : [];
      const metrics = metricsResult.status === "fulfilled" ? metricsResult.value : null;
      const media = mediaResult.status === "fulfilled" && mediaResult.value?.items
        ? mediaResult.value.items
        : [];
      const dashboard = dashboardResult.status === "fulfilled" ? dashboardResult.value : null;

      if (testimonialsResult.status === "rejected") loadIssues.push("testimonios");
      if (metricsResult.status === "rejected") loadIssues.push("metricas");
      if (mediaResult.status === "rejected") loadIssues.push("media");
      if (dashboardResult.status === "rejected") loadIssues.push("dashboard");

      const visibleMedia = media.filter((item) => item.status !== "archived");
      const missingAlt = visibleMedia.filter(
        (item) => (item.mime_type || "").startsWith("image/") && !String(item.alt_text || "").trim(),
      ).length;

      setRecentTestimonials(testimonials.slice(0, 5));
      setTopPages(dashboard?.top_pages ?? []);
      setRecentPosts(dashboard?.recent_posts ?? []);
      setRecentActivity(dashboard?.recent_activity ?? []);
      setPubsChart(dashboard?.publicaciones_por_mes ?? []);
      setContentTypeChart(dashboard?.contenido_por_tipo ?? []);
      setStats({
        testimonials: testimonials.length,
        pendingTestimonials: testimonials.filter((testimony) => !testimony.is_approved && testimony.status !== "archived").length,
        approvedTestimonials: metrics?.testimonials_approved ?? testimonials.filter((testimony) => testimony.is_approved).length,
        sections: SITE_BLOCKS.length,
        publishedBlocks: metrics?.published_blocks ?? 0,
        inReviewBlocks: metrics?.in_review_blocks ?? 0,
        activeAnnouncements: metrics?.announcements_active ?? 0,
        mediaTotal: metrics?.media_total ?? visibleMedia.length,
        mediaImages: metrics?.media_images ?? visibleMedia.filter((item) => (item.mime_type || "").startsWith("image/")).length,
        mediaVideos: metrics?.media_videos ?? visibleMedia.filter((item) => (item.mime_type || "").startsWith("video/")).length,
        mediaAudio: metrics?.media_audio ?? visibleMedia.filter((item) => (item.mime_type || "").startsWith("audio/")).length,
        mediaWithoutAlt: missingAlt,
        pageViewsTotal: dashboard?.page_views_total ?? 0,
        pageViews7d: dashboard?.page_views_7d ?? 0,
        pageViews30d: dashboard?.page_views_30d ?? 0,
        postsTotal: dashboard?.posts_total ?? 0,
        postsPublished: dashboard?.posts_published ?? 0,
        categoriesTotal: dashboard?.categories_total ?? 0,
        tagsTotal: dashboard?.tags_total ?? 0,
      });
      setDataIssue(loadIssues.length ? `No se pudieron cargar: ${loadIssues.join(", ")}.` : null);
      setLoading(false);
    };

    fetchData().catch(() => {
      toast.error("Error al cargar dashboard");
      setDataIssue("No se pudo cargar el resumen del sitio.");
      setRecentTestimonials([]);
      setStats(EMPTY_STATS);
      setLoading(false);
    });
  }, [canEdit, token]);

  const quickLinks = useMemo(
    () => [
      { label: "Paginas", href: "/plataforma/cms/pages", description: "Contenido, SEO y estados", icon: FileText, show: canEdit },
      { label: "Posts / Blog", href: "/plataforma/cms/posts", description: "Articulos y noticias", icon: BookOpen, show: canEdit },
      { label: "Categorias", href: "/plataforma/cms/categories", description: "Taxonomias de posts", icon: Globe, show: canEdit },
      { label: "Etiquetas", href: "/plataforma/cms/tags", description: "Tags de posts", icon: Tag, show: canEdit },
      { label: "Menus", href: "/plataforma/cms/menus", description: "Navegacion publica", icon: Link2, show: canEdit },
      { label: "Testimonios", href: "/plataforma/cms/testimonials", description: "Aprobacion y portada", icon: MessageCircle, show: canEdit },
      { label: "Builder", href: "/plataforma/cms/builder", description: "Secciones visuales", icon: PanelsTopLeft, show: canEdit },
      { label: "Media", href: "/plataforma/cms/media", description: "Archivos y accesibilidad", icon: ImageIcon, show: canEdit },
      { label: "Temas", href: "/plataforma/cms/themes", description: "Tokens por sitio", icon: Palette, show: canEdit },
      { label: "Equipo Pastoral", href: "/plataforma/cms/pastoral-team", description: "Perfiles y redes sociales", icon: Users, show: canEdit },
      { label: "Sitios", href: "/plataforma/cms/sites", description: "Portales y dominios", icon: Globe, show: canManage },
      { label: "Auditoría SEO", href: "/plataforma/cms/seo-audit", description: "Score y hallazgos por página", icon: Gauge, show: canEdit },
    ].filter((link) => link.show),
    [canEdit, canManage],
  );

  const qualityChecks: QualityCheck[] = useMemo(
    () => [
      {
        label: "Testimonios pendientes",
        description: stats.pendingTestimonials > 0 ? "Historias esperando revision editorial" : "Cola de testimonios limpia",
        value: stats.pendingTestimonials,
        href: "/plataforma/cms/testimonials",
        tone: stats.pendingTestimonials > 0 ? "warning" : "success",
        icon: MessageCircle,
      },
      {
        label: "Bloques en revision",
        description: stats.inReviewBlocks > 0 ? "Contenido listo para aprobar o devolver" : "Sin bloque esperando aprobacion",
        value: stats.inReviewBlocks,
        href: "/plataforma/cms/pages",
        tone: stats.inReviewBlocks > 0 ? "warning" : "success",
        icon: Clock3,
      },
      {
        label: "Imagenes sin alt",
        description: stats.mediaWithoutAlt > 0 ? "Completa metadata accesible en media" : "Imagenes activas con texto alternativo",
        value: stats.mediaWithoutAlt,
        href: "/plataforma/cms/media",
        tone: stats.mediaWithoutAlt > 0 ? "warning" : "success",
        icon: ImageIcon,
      },
      {
        label: "Bloques publicados",
        description: stats.publishedBlocks > 0 ? "Contenido visible para el sitio" : "Aun no hay bloques publicados",
        value: stats.publishedBlocks,
        href: "/plataforma/cms/pages",
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
    { label: "Testimonios publicados", value: stats.approvedTestimonials, icon: MessageCircle, href: "/plataforma/cms/testimonials" },
    { label: "Pendientes", value: stats.pendingTestimonials, icon: AlertCircle, href: "/plataforma/cms/testimonials" },
    { label: "Media total", value: stats.mediaTotal, icon: ImageIcon, href: "/plataforma/cms/media" },
    { label: "Imagenes", value: stats.mediaImages, icon: ImageIcon, href: "/plataforma/cms/media" },
    { label: "Videos", value: stats.mediaVideos, icon: Video, href: "/plataforma/cms/media" },
    { label: "Podcasts", value: stats.mediaAudio, icon: Volume2, href: "/plataforma/cms/media" },
    { label: "Bloques del sitio", value: stats.sections, icon: Layers3, href: "/plataforma/cms/builder" },
    { label: "Publicados", value: stats.publishedBlocks, icon: CheckCircle2, href: "/plataforma/cms/pages" },
    { label: "En revision", value: stats.inReviewBlocks, icon: Clock3, href: "/plataforma/cms/pages" },
    { label: "Anuncios activos", value: stats.activeAnnouncements, icon: Megaphone, href: "/plataforma/cms/pages" },
    { label: "Vistas totales", value: stats.pageViewsTotal, icon: Eye, href: "/plataforma/cms/audit" },
    { label: "Vistas 7d", value: stats.pageViews7d, icon: TrendingUp, href: "/plataforma/cms/audit" },
    { label: "Vistas 30d", value: stats.pageViews30d, icon: TrendingUp, href: "/plataforma/cms/audit" },
    { label: "Posts", value: stats.postsTotal, icon: BookOpen, href: "/plataforma/cms/posts" },
    { label: "Posts publicados", value: stats.postsPublished, icon: CheckCircle2, href: "/plataforma/cms/posts" },
    { label: "Categorías", value: stats.categoriesTotal, icon: Globe, href: "/plataforma/cms/categories" },
    { label: "Etiquetas", value: stats.tagsTotal, icon: Tag, href: "/plataforma/cms/tags" },
  ];

  const maxPubValue = useMemo(() => {
    if (!pubsChart.length) return 1;
    return Math.max(...pubsChart.map((d) => d.value), 1);
  }, [pubsChart]);

  const maxTypeValue = useMemo(() => {
    if (!contentTypeChart.length) return 1;
    return Math.max(...contentTypeChart.map((d) => d.value), 1);
  }, [contentTypeChart]);

  if (!isAuthenticated) {
    return (
      <div className="h-full overflow-y-auto">
        <div className="mx-auto max-w-3xl px-4 py-1.5 text-center">
          <h1 className="text-xl font-semibold">Inicia sesion</h1>
          <p className="mt-3 text-[hsl(var(--text-secondary))]">Necesitas una sesion valida para administrar el sitio.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-[hsl(var(--surface-1))]/60 dark:bg-[hsl(var(--admin-bg-primary))]">
      <div className="space-y-3 px-4 py-2 lg:px-3">
        {dataIssue && (
          <div className="flex items-start gap-3 rounded-lg border border-[hsl(var(--warning)/25%)] bg-warning-soft px-4 py-3 text-sm text-warning-text dark:border-[hsl(var(--warning)/100%)]/30 dark:bg-[hsl(var(--warning))]/10 dark:text-[hsl(var(--warning))]">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{dataIssue}</span>
          </div>
        )}

        {/* Public site shortcut */}
        <div className="flex items-center justify-end gap-2">
          <a
            href="/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--info)/30%)] hover:text-[hsl(var(--primary))] dark:border-white/10 dark:text-[hsl(var(--text-secondary))]"
          >
            Ver sitio público
            <ExternalLink size={14} />
          </a>
        </div>

        {/* Metric cards */}
        <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {metricCards.map((metric) => {
            const Icon = metric.icon;
            return (
              <Link key={metric.label} href={metric.href} className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-4 shadow-sm dark:border-white/10 dark:bg-[hsl(var(--admin-bg-tertiary))] transition-colors hover:border-[hsl(var(--info)/30%)] dark:hover:border-[hsl(var(--info)/100%)]/50">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{metric.label}</p>
                  <Icon size={15} className="text-[hsl(var(--text-secondary))]" />
                </div>
                <p className="mt-3 text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white">
                  {metricValue(metric.value, loading)}
                </p>
              </Link>
            );
          })}
        </section>

        {/* Charts row */}
        <section className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[hsl(var(--admin-bg-tertiary))]">
            <div className="mb-3">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tendencias</p>
              <h2 className="mt-1 text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white">Publicaciones por mes</h2>
            </div>
            {pubsChart.length > 0 ? (
              <div className="flex items-end gap-2 h-40">
                {pubsChart.map((d) => (
                  <div key={d.label} className="flex-1 flex flex-col items-center gap-1">
                    <div
                      className="w-full rounded-t bg-[hsl(var(--primary))] opacity-80 hover:opacity-100 transition-all"
                      style={{ height: `${Math.max((d.value / maxPubValue) * 100, 4)}%` }}
                      title={`${d.label}: ${Math.round(d.value)}`}
                    />
                    <span className="text-[10px] text-[hsl(var(--text-secondary))]">{d.label}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[hsl(var(--text-secondary))]">Sin datos de publicación.</p>
            )}
          </div>

          <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[hsl(var(--admin-bg-tertiary))]">
            <div className="mb-3">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Contenido</p>
              <h2 className="mt-1 text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white">Secciones por tipo</h2>
            </div>
            {contentTypeChart.length > 0 ? (
              <div className="space-y-2">
                {contentTypeChart.map((d) => (
                  <div key={d.label} className="flex items-center gap-3">
                    <span className="w-24 text-xs text-[hsl(var(--text-secondary))] truncate">{d.label}</span>
                    <div className="flex-1 h-4 rounded bg-[hsl(var(--surface-1))] dark:bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded bg-[hsl(var(--success))]/80"
                        style={{ width: `${Math.max((d.value / maxTypeValue) * 100, 2)}%` }}
                      />
                    </div>
                    <span className="w-8 text-right text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white">{Math.round(d.value)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-[hsl(var(--text-secondary))]">Sin datos de secciones.</p>
            )}
          </div>
        </section>

        {/* Quality + Role */}
        <section className="grid grid-cols-1 gap-3 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[hsl(var(--admin-bg-tertiary))]">
            <div className="flex flex-col gap-3 border-b border-[hsl(var(--border))] pb-4 dark:border-white/10 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Control de calidad</p>
                <h2 className="mt-1 text-xl font-semibold text-[hsl(var(--text-primary))] dark:text-white">Prioridades editoriales</h2>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-14 items-center justify-center rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-sm font-semibold text-[hsl(var(--text-primary))] dark:border-white/10 dark:bg-white/5 dark:text-white">
                  {qualityScore === null ? "..." : `${qualityScore}%`}
                </div>
                <p className="max-w-44 text-xs leading-relaxed text-[hsl(var(--text-secondary))]">
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
                    className="group rounded-lg border border-[hsl(var(--border))] p-4 transition-colors hover:border-[hsl(var(--info)/30%)] dark:border-white/10 dark:hover:border-[hsl(var(--info)/100%)]/50"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className={isWarning ? "rounded-lg bg-warning-soft p-2 text-warning-text dark:bg-[hsl(var(--warning))]/10 dark:text-warning-text" : "rounded-lg bg-success-soft p-2 text-success-text dark:bg-[hsl(var(--success))]/10 dark:text-success-text"}>
                          <Icon size={16} />
                        </div>
                        <div>
                          <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{check.label}</p>
                          <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">{check.description}</p>
                        </div>
                      </div>
                      <span className={isWarning ? "text-lg font-semibold text-warning-text dark:text-warning-text" : "text-lg font-semibold text-success-text dark:text-success-text"}>
                        {loading ? "..." : check.value}
                      </span>
                    </div>
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[hsl(var(--admin-bg-tertiary))]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Acceso</p>
                <h2 className="mt-1 text-xl font-semibold text-[hsl(var(--text-primary))] dark:text-white">Rol editorial</h2>
              </div>
              <ShieldCheck className="h-5 w-5 text-[hsl(var(--primary))]" />
            </div>
            <p className="mt-3 text-sm leading-relaxed text-[hsl(var(--text-secondary))]">
              {canManage
                ? "Puedes administrar sitios, contenido, temas y publicacion."
                : canEdit
                  ? "Puedes editar contenido, media, eventos y flujos editoriales."
                  : "Tienes acceso de lectura al resumen. Solicita un rol editorial para modificar contenido."}
            </p>

            <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {quickLinks.map(({ label, href, description, icon: Icon }) => (
                <Link key={href} href={href} className="rounded-lg border border-[hsl(var(--border))] p-3 transition-colors hover:border-[hsl(var(--info)/30%)] dark:border-white/10 dark:hover:border-[hsl(var(--info)/100%)]/50">
                  <div className="flex items-center gap-2">
                    <Icon size={15} className="text-[hsl(var(--primary))]" />
                    <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{label}</p>
                  </div>
                  <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">{description}</p>
                </Link>
              ))}
              {quickLinks.length === 0 && (
                <div className="rounded-lg border border-dashed border-[hsl(var(--border))] p-4 text-sm text-[hsl(var(--text-secondary))] dark:border-white/10">
                  No hay modulos de edicion disponibles para tu rol actual.
                </div>
              )}
            </div>
          </div>
        </section>

        {/* Top pages + Recent posts + Activity */}
        <section className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          {/* Top pages */}
          <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[hsl(var(--admin-bg-tertiary))]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white">Páginas más vistas</h2>
                <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Últimos 30 días.</p>
              </div>
              <Eye className="h-5 w-5 text-[hsl(var(--primary))]" />
            </div>
            <div className="mt-4 space-y-2">
              {loading ? (
                <p className="text-sm text-[hsl(var(--text-secondary))]">Cargando...</p>
              ) : topPages.length === 0 ? (
                <p className="rounded-lg border border-dashed border-[hsl(var(--border))] p-4 text-sm text-[hsl(var(--text-secondary))] dark:border-white/10">
                  Sin vistas registradas.
                </p>
              ) : (
                topPages.map((page, idx) => (
                  <div key={page.slug} className="flex items-center justify-between gap-3 rounded-lg border border-[hsl(var(--border))] p-3 dark:border-white/10">
                    <div className="flex items-center gap-3">
                      <span className="flex h-6 w-6 items-center justify-center rounded bg-[hsl(var(--surface-1))] text-[10px] font-bold text-[hsl(var(--text-secondary))] dark:bg-white/5">
                        {idx + 1}
                      </span>
                      <div>
                        <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate max-w-[140px]">{page.title}</p>
                        <p className="text-[11px] text-[hsl(var(--text-secondary))]">/{page.slug}</p>
                      </div>
                    </div>
                    <span className="text-sm font-bold text-[hsl(var(--primary))]">{page.views}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent posts */}
          <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[hsl(var(--admin-bg-tertiary))]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white">Posts recientes</h2>
                <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Últimos publicados.</p>
              </div>
              {canEdit && (
                <Link href="/plataforma/cms/posts" className="rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--info)/30%)] hover:text-[hsl(var(--primary))] dark:border-white/10 dark:text-[hsl(var(--text-secondary))]">
                  Ver todo
                </Link>
              )}
            </div>
            <div className="mt-4 space-y-3">
              {loading ? (
                <p className="text-sm text-[hsl(var(--text-secondary))]">Cargando posts...</p>
              ) : recentPosts.length === 0 ? (
                <p className="rounded-lg border border-dashed border-[hsl(var(--border))] p-4 text-sm text-[hsl(var(--text-secondary))] dark:border-white/10">
                  Sin posts publicados.
                </p>
              ) : (
                recentPosts.map((post) => (
                  <div key={post.slug} className="rounded-lg border border-[hsl(var(--border))] p-3 dark:border-white/10">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white truncate">{post.title}</p>
                      <span className="shrink-0 rounded-full bg-success-soft px-2 py-0.5 text-[10px] font-bold text-success-text dark:bg-[hsl(var(--success))]/10 dark:text-success-text">
                        {post.status}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-[11px] text-[hsl(var(--text-secondary))]">
                      <span>{post.published_at}</span>
                      {post.category_count > 0 && <span>· {post.category_count} cat</span>}
                      {post.tag_count > 0 && <span>· {post.tag_count} tags</span>}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent activity */}
          <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[hsl(var(--admin-bg-tertiary))]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white">Actividad reciente</h2>
                <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Últimas acciones en el CMS.</p>
              </div>
              <Clock3 className="h-5 w-5 text-[hsl(var(--primary))]" />
            </div>
            <div className="mt-4 space-y-3">
              {loading ? (
                <p className="text-sm text-[hsl(var(--text-secondary))]">Cargando actividad...</p>
              ) : recentActivity.length === 0 ? (
                <p className="rounded-lg border border-dashed border-[hsl(var(--border))] p-4 text-sm text-[hsl(var(--text-secondary))] dark:border-white/10">
                  Sin actividad reciente.
                </p>
              ) : (
                recentActivity.map((activity, idx) => (
                  <div key={idx} className="flex items-start gap-3 rounded-lg border border-[hsl(var(--border))] p-3 dark:border-white/10">
                    <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-[hsl(var(--primary))]" />
                    <div className="min-w-0">
                      <p className="text-sm text-[hsl(var(--text-primary))] dark:text-white">{activityLabel(activity)}</p>
                      {activity.from_status && activity.to_status && (
                        <p className="mt-0.5 text-[11px] text-[hsl(var(--text-secondary))]">
                          {activity.from_status} → {activity.to_status}
                        </p>
                      )}
                      <p className="mt-1 text-[11px] text-[hsl(var(--text-secondary))]">{activity.created_at}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        {/* Testimonials + Workflow */}
        <section className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[hsl(var(--admin-bg-tertiary))]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white">Testimonios recientes</h2>
                <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Ultimas historias recibidas para revision y publicacion.</p>
              </div>
              {canEdit && (
                <Link href="/plataforma/cms/testimonials" className="rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--info)/30%)] hover:text-[hsl(var(--primary))] dark:border-white/10 dark:text-[hsl(var(--text-secondary))]">
                  Ver todo
                </Link>
              )}
            </div>

            <div className="mt-4 space-y-3">
              {loading ? (
                <p className="text-sm text-[hsl(var(--text-secondary))]">Cargando historias...</p>
              ) : recentTestimonials.length === 0 ? (
                <p className="rounded-lg border border-dashed border-[hsl(var(--border))] p-4 text-sm text-[hsl(var(--text-secondary))] dark:border-white/10">
                  Sin testimonios en la cola.
                </p>
              ) : (
                recentTestimonials.map((testimony) => (
                  <div key={testimony.id} className="rounded-lg border border-[hsl(var(--border))] p-4 dark:border-white/10">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{testimony.emotion || "Sin categoria"}</p>
                      <span className={testimony.is_approved ? "rounded-full bg-success-soft px-2 py-1 text-[10px] font-bold text-success-text dark:bg-[hsl(var(--success))]/10 dark:text-success-text" : "rounded-full bg-warning-soft px-2 py-1 text-[10px] font-bold text-warning-text dark:bg-[hsl(var(--warning))]/10 dark:text-warning-text"}>
                        {testimony.is_approved ? "Aprobado" : "Pendiente"}
                      </span>
                    </div>
                    <p className="mt-2 line-clamp-2 text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{testimony.content}</p>
                    <p className="mt-3 text-[11px] text-[hsl(var(--text-secondary))]">{formatDate(testimony.created_at)}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:border-white/10 dark:bg-[hsl(var(--admin-bg-tertiary))]">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white">Ruta de gestion</h2>
                <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Secuencia recomendada para publicar cambios del sitio.</p>
              </div>
              <CheckCircle2 className="h-5 w-5 text-success-text" />
            </div>
            <div className="mt-5 space-y-3">
              {[
                { label: "Editar estructura", detail: "Paginas, menus y secciones del builder.", href: "/plataforma/cms/pages" },
                { label: "Completar media", detail: "Alt text, etiquetas y archivos reutilizables.", href: "/plataforma/cms/media" },
                { label: "Revisar contenido", detail: "Testimonios, bloques en revision y eventos.", href: "/plataforma/cms/pages" },
                { label: "Publicar", detail: "Aprobar, publicar y revisar el sitio en vivo.", href: "/", external: true },
              ].map((step, index) => (
                <Link
                  key={step.label}
                  href={step.href}
                  target={step.external ? "_blank" : undefined}
                  rel={step.external ? "noopener noreferrer" : undefined}
                  className="flex items-start gap-3 rounded-lg border border-[hsl(var(--border))] p-3 transition-colors hover:border-[hsl(var(--info)/30%)] dark:border-white/10 dark:hover:border-[hsl(var(--info)/100%)]/50"
                >
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[hsl(var(--bg-muted))] text-xs font-semibold text-white dark:bg-[hsl(var(--bg-primary))] dark:text-[hsl(var(--text-primary))]">
                    {index + 1}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="flex items-center gap-1.5 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">
                      {step.label}
                      {step.external && <ExternalLink size={14} className="text-[hsl(var(--text-secondary))]" />}
                    </span>
                    <span className="mt-1 block text-xs text-[hsl(var(--text-secondary))]">{step.detail}</span>
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

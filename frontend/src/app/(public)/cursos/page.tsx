"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, CheckCircle2, Clock, User, Sparkles } from "lucide-react";
import { apiFetch } from "@/lib/http";
import { SITE_KEY } from "@/lib/site-config";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import PublicHeroWithSlides, { type PublicSlide } from "@/components/public/PublicHeroWithSlides";
import RichText from "@/components/public/RichText";
import type { CourseSummary } from "@/types/academy";
import type { CmsSection } from "@/types/cms-v2";

type PublicCourse = CourseSummary & {
  slug?: string;
  image_url?: string | null;
  instructor_name?: string | null;
  cta?: string;
  lessons?: number;
  instructor?: string;
  modality?: string;
  imageUrl?: string;
};

// ─── Module-scope Subcomponents ──────────────────────────────────────────────

function CursosHeroSection({
  section,
  fallbackHero,
  courses,
}: {
  section?: CmsSection;
  fallbackHero?: Record<string, unknown> | null;
  courses: PublicCourse[];
}) {
  const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
  const fallback = fallbackHero ?? {};

  const eyebrow = typeof raw.eyebrow === "string" ? raw.eyebrow : typeof fallback.eyebrow === "string" ? fallback.eyebrow : "";
  const titleLead = typeof raw.title_lead === "string" ? raw.title_lead : typeof fallback.title_lead === "string" ? fallback.title_lead : "Nuestra";
  const titleAccent = typeof raw.title_accent === "string" ? raw.title_accent : typeof fallback.title_accent === "string" ? fallback.title_accent : "Academia";
  const description = typeof raw.description === "string" ? raw.description : typeof fallback.description === "string" ? fallback.description : "";

  // Prioridad 1: Slides configurados explícitamente en el CMS
  const rawSlides = Array.isArray(raw.slides) && raw.slides.length > 0
    ? (raw.slides as Array<{ src?: string; alt?: string; title?: string; caption?: string; href?: string }>)
    : Array.isArray(fallback.slides) && fallback.slides.length > 0
    ? (fallback.slides as Array<{ src?: string; alt?: string; title?: string; caption?: string; href?: string }>)
    : [];

  const cmsSlides: PublicSlide[] = rawSlides
    .filter((s) => s && typeof s.src === "string" && s.src.trim() !== "")
    .map((s) => ({
      src: s.src!,
      alt: s.alt || `${titleLead} ${titleAccent}`,
      title: s.title || undefined,
      caption: s.caption || undefined,
      href: s.href || undefined,
    }));

  // Prioridad 2: Si el CMS no tiene slides manuales, armar carrusel dinámico de los primeros 4 cursos
  const autoCourseSlides: PublicSlide[] = courses.slice(0, 4).map((c) => ({
    src: c.image_url || c.imageUrl || "/og-default.png",
    alt: c.title,
    title: c.title,
    caption: c.description || c.title,
    href: `/cursos/${c.slug || c.id}`,
  }));

  const slides: PublicSlide[] = cmsSlides.length > 0
    ? cmsSlides
    : autoCourseSlides.length > 0
    ? autoCourseSlides
    : [
        {
          src: "/og-default.png",
          alt: `${titleLead} ${titleAccent}`,
          title: titleLead ? `${titleLead} ${titleAccent}` : "Academia CCF",
          caption: description || undefined,
        },
      ];

  const hasHero = Boolean(titleLead || titleAccent || description || eyebrow);
  if (!hasHero) return null;

  return (
    <section data-testid="public-cursos-hero" data-section-key="hero">
      <PublicHeroWithSlides
        eyebrow={eyebrow}
        titleLead={titleLead}
        titleAccent={titleAccent}
        description={description}
        slides={slides}
      />
    </section>
  );
}

function CursosCatalogSection({
  section,
  fallbackFeed,
  courses,
  loading,
  error,
  onRetry,
}: {
  section?: CmsSection;
  fallbackFeed?: Record<string, unknown> | null;
  courses: PublicCourse[];
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}) {
  const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
  const fallback = fallbackFeed ?? {};

  const coursesTitle = (raw.courses_title as string) || (fallback.courses_title as string) || "Nuestra Academia";
  const coursesDescription = (raw.courses_description as string) || (fallback.courses_description as string) || "Cursos diseñados para fortalecer tu fe, edificar tu familia y capacitarte en el servicio ministerial.";
  const featuredBadge = (raw.featured_badge as string) || (fallback.featured_badge as string) || "Acceso Gratuito";
  const featuredCta = (raw.featured_cta as string) || (fallback.featured_cta as string) || "Inscribirme Gratis";
  const featuredImage = (raw.featured_image as string) || (raw.hero_image_url as string) || (fallback.featured_image as string) || (fallback.hero_image_url as string) || "";
  const emptyTitle = (raw.empty_title as string) || (fallback.empty_title as string) || "No hay cursos disponibles en este momento";
  const emptyDescription = (raw.empty_description as string) || (fallback.empty_description as string) || "Próximamente publicaremos nuevas convocatorias formativas.";
  const errorTitle = (raw.error_title as string) || "No pudimos cargar los cursos";
  const errorDescription = (raw.error_description as string) || "Intenta recargar la página en unos segundos.";
  const retryButtonText = (raw.retry_button_text as string) || "Reintentar";

  const featured = courses[0];
  const rest = courses.slice(1);

  const savePendingCourse = (course: PublicCourse) => {
    try {
      const payload = JSON.stringify({ id: course.id, slug: course.slug, title: course.title });
      localStorage.setItem("ccf_pending_course", payload);
      document.cookie = `ccf_pending_course=${encodeURIComponent(payload)}; path=/; max-age=86400; SameSite=Lax`;
    } catch {
      // Ignorar errores de cookies/storage
    }
  };

  return (
    <section
      data-testid="public-cursos-catalog"
      data-section-key="feed"
      className="ccf-section ccf-container"
    >
      {/* Encabezado de la Sección */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-12 gap-4">
        <div className="max-w-2xl">
          {coursesTitle && (
            <h2
              className="ccf-headline text-3xl md:text-4xl font-black mb-3 tracking-tight"
              style={{ color: "var(--site-on-surface)" }}
            >
              {coursesTitle}
            </h2>
          )}
          {coursesDescription && (
            <RichText
              html={coursesDescription}
              className="ccf-body text-base md:text-lg text-site-on-surface-variant"
            />
          )}
        </div>
      </div>

      {/* Estados de Carga y Error */}
      {loading ? (
        <div className="py-20 flex justify-center items-center">
          <div
            className="w-10 h-10 border-4 border-t-transparent rounded-full animate-spin"
            style={{ borderColor: "var(--site-primary) transparent transparent transparent" }}
          />
        </div>
      ) : error ? (
        <div
          className="rounded-2xl p-10 text-center border border-site-outline-variant/30"
          style={{ background: "var(--site-surface-container-low)" }}
        >
          <h3 className="text-xl font-bold mb-2 text-site-on-surface">{errorTitle}</h3>
          <p className="text-sm mb-5 text-site-on-surface-variant max-w-md mx-auto">{errorDescription}</p>
          <button
            type="button"
            onClick={onRetry}
            className="ccf-button"
            style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}
          >
            {retryButtonText}
          </button>
        </div>
      ) : featured ? (
        <div className="space-y-12">
          {/* Fila Principal: Destacado + 3 Tarjetas Secundarias */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            {/* Tarjeta Destacada Principal */}
            <motion.article
              className="md:col-span-8 group relative rounded-3xl overflow-hidden min-h-[320px] md:min-h-[460px] cursor-pointer shadow-lg border border-site-outline-variant/20"
              style={{ background: "var(--site-surface-container-low)" }}
              whileHover={{ y: -3 }}
              transition={{ duration: 0.2 }}
            >
              <Link
                href={`/cursos/${featured.slug || featured.id}`}
                onClick={() => savePendingCourse(featured)}
                className="absolute inset-0 z-20"
                aria-label={featured.title}
              />
              <div className="absolute inset-0">
                <Image
                  src={featuredImage || featured.image_url || featured.imageUrl || "/og-default.png"}
                  alt={featured.title}
                  fill
                  className="object-cover transition-transform duration-700 group-hover:scale-105"
                  style={{ opacity: 0.6 }}
                />
              </div>
              <div
                className="absolute inset-0"
                style={{
                  background:
                    "linear-gradient(to top, rgba(0,0,0,0.85) 0%, rgba(0,0,0,0.4) 50%, transparent 100%)",
                }}
              />
              <div className="absolute bottom-0 p-6 md:p-8 w-full z-10 flex flex-col justify-end h-full">
                <span
                  className="inline-flex items-center gap-1.5 self-start px-3.5 py-1 rounded-full text-xs font-bold uppercase tracking-wide mb-3 shadow-md"
                  style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}
                >
                  <Sparkles size={12} /> {featured.modality || featuredBadge}
                </span>
                <h3 className="text-2xl md:text-3xl lg:text-4xl font-black mb-3 text-white drop-shadow-md">
                  {featured.title}
                </h3>
                <p className="text-sm md:text-base leading-relaxed max-w-2xl mb-5 text-white/85 line-clamp-3">
                  {featured.description || featured.title}
                </p>
                <div className="flex items-center gap-4 text-xs font-semibold text-white/75 mb-5">
                  {featured.lessons ? (
                    <span className="inline-flex items-center gap-1">
                      <Clock size={13} /> {featured.lessons} lecciones
                    </span>
                  ) : null}
                  {featured.instructor || featured.instructor_name ? (
                    <span className="inline-flex items-center gap-1">
                      <User size={13} /> {featured.instructor || featured.instructor_name}
                    </span>
                  ) : null}
                </div>
                <span className="inline-flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-white group-hover:translate-x-1 transition-transform">
                  {featured.cta || featuredCta} <ArrowRight size={16} />
                </span>
              </div>
            </motion.article>

            {/* Tarjetas Laterales (Hasta 3) */}
            <div className="md:col-span-4 grid gap-4">
              {rest.slice(0, 3).map((course) => (
                <motion.article
                  key={course.id}
                  className="group rounded-2xl overflow-hidden border bg-site-surface-container-low border-site-outline-variant/30 hover:border-site-primary/40 transition-colors shadow-sm"
                  whileHover={{ y: -2 }}
                >
                  <Link
                    href={`/cursos/${course.slug || course.id}`}
                    onClick={() => savePendingCourse(course)}
                    className="block"
                  >
                    <div className="relative h-36 bg-site-surface-container overflow-hidden">
                      <Image
                        src={course.image_url || course.imageUrl || "/og-default.png"}
                        alt={course.title}
                        fill
                        className="object-cover transition-transform duration-500 group-hover:scale-105"
                      />
                      <div className="absolute top-3 left-3">
                        <span
                          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-2xs font-bold uppercase tracking-wider shadow-sm"
                          style={{
                            background: "var(--site-surface)",
                            color: "var(--site-primary)",
                          }}
                        >
                          {course.modality || "Gratuito"}
                        </span>
                      </div>
                    </div>
                    <div className="p-4">
                      <h4 className="font-bold text-site-on-surface text-base line-clamp-1 group-hover:text-site-primary transition-colors">
                        {course.title}
                      </h4>
                      <p className="mt-1 text-xs text-site-on-surface-variant line-clamp-2 leading-relaxed">
                        {course.description || course.title}
                      </p>
                      <div className="mt-3 flex items-center justify-between text-2xs text-site-on-surface-variant font-medium">
                        {course.lessons ? (
                          <span className="inline-flex items-center gap-1">
                            <Clock size={11} /> {course.lessons} clases
                          </span>
                        ) : (
                          <span />
                        )}
                        <span className="font-bold text-site-primary inline-flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                          Ver detalles <ArrowRight size={11} />
                        </span>
                      </div>
                    </div>
                  </Link>
                </motion.article>
              ))}
            </div>
          </div>

          {/* Cuadrícula de Cursos Restantes (4 en adelante) */}
          {rest.length > 3 && (
            <div className="pt-6 border-t border-site-outline-variant/20">
              <h3 className="text-xl font-bold mb-6 text-site-on-surface">Más Cursos de la Academia</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {rest.slice(3).map((course) => (
                  <Link
                    key={course.id}
                    href={`/cursos/${course.slug || course.id}`}
                    onClick={() => savePendingCourse(course)}
                    className="group rounded-2xl border p-5 bg-site-surface-container-low border-site-outline-variant/30 hover:border-site-primary/40 hover:shadow-md transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-3 mb-3">
                        <span
                          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-2xs font-bold uppercase tracking-wider"
                          style={{
                            background: "var(--site-surface-container)",
                            color: "var(--site-primary)",
                          }}
                        >
                          {course.modality || "Gratuito"}
                        </span>
                        <CheckCircle2 size={16} className="text-site-primary" />
                      </div>
                      <h4 className="font-bold text-base mb-2 text-site-on-surface group-hover:text-site-primary transition-colors">
                        {course.title}
                      </h4>
                      <p className="text-xs text-site-on-surface-variant line-clamp-3 leading-relaxed">
                        {course.description || course.title}
                      </p>
                    </div>
                    <div className="mt-5 pt-3 border-t border-site-outline-variant/15 flex items-center justify-between text-2xs text-site-on-surface-variant">
                      <div className="flex items-center gap-3">
                        {course.lessons ? (
                          <span className="inline-flex items-center gap-1">
                            <Clock size={12} /> {course.lessons} clases
                          </span>
                        ) : null}
                        {course.instructor || course.instructor_name ? (
                          <span className="inline-flex items-center gap-1 truncate max-w-[120px]">
                            <User size={12} /> {course.instructor || course.instructor_name}
                          </span>
                        ) : null}
                      </div>
                      <span className="font-bold text-site-primary inline-flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                        Entrar <ArrowRight size={11} />
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div
          className="rounded-2xl p-12 text-center border border-site-outline-variant/30"
          style={{ background: "var(--site-surface-container-low)" }}
        >
          {emptyTitle && <h3 className="text-xl font-bold mb-2 text-site-on-surface">{emptyTitle}</h3>}
          {emptyDescription && (
            <p className="text-sm text-site-on-surface-variant max-w-md mx-auto">{emptyDescription}</p>
          )}
        </div>
      )}
    </section>
  );
}

function CursosCtaSection({
  section,
  fallbackFeed,
}: {
  section?: CmsSection;
  fallbackFeed?: Record<string, unknown> | null;
}) {
  const raw = (section?.props_json as Record<string, unknown> | undefined) ?? {};
  const fallback = fallbackFeed ?? {};

  const ctaTitle = (raw.cta_title as string) || (fallback.cta_title as string) || "";
  const ctaDesc = (raw.cta_desc as string) || (fallback.cta_desc as string) || "";
  const ctaLabel = (raw.cta_label as string) || (fallback.cta_label as string) || "";
  const ctaHref = (raw.cta_href as string) || (fallback.cta_href as string) || "";
  const secondaryCtaLabel = (raw.secondary_cta_label as string) || (fallback.secondary_cta_label as string) || "";
  const secondaryCtaHref = (raw.secondary_cta_href as string) || (fallback.secondary_cta_href as string) || "";

  if (!ctaTitle && !ctaDesc) return null;

  return (
    <section
      data-testid="public-cursos-cta"
      data-section-key="cta"
      className="ccf-section-tight ccf-container mb-12"
    >
      <div
        className="relative rounded-3xl overflow-hidden p-8 md:p-12 lg:p-14 text-center shadow-xl"
        style={{
          background: "var(--site-cta-gradient)",
          boxShadow: "var(--site-cta-shadow)",
        }}
      >
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.12),transparent_60%)] pointer-events-none" />
        <div className="relative z-10 max-w-2xl mx-auto">
          {ctaTitle && (
            <h2 className="ccf-headline text-2xl md:text-3xl lg:text-4xl font-black text-white mb-4">
              {ctaTitle}
            </h2>
          )}
          {ctaDesc && (
            <RichText
              html={ctaDesc}
              className="ccf-body text-sm md:text-base text-white/80 mb-8 leading-relaxed"
            />
          )}
          <div className="flex flex-wrap items-center justify-center gap-4">
            {ctaLabel && (
              <a
                href={ctaHref || "https://wa.me/573001234567"}
                target={ctaHref.startsWith("http") ? "_blank" : undefined}
                rel={ctaHref.startsWith("http") ? "noopener noreferrer" : undefined}
                className="ccf-button bg-site-surface text-site-primary shadow-xl font-bold hover:scale-105 transition-transform"
              >
                {ctaLabel} <ArrowRight size={14} />
              </a>
            )}
            {secondaryCtaLabel && (
              <Link
                href={secondaryCtaHref || "/sedes"}
                className="ccf-button bg-white/15 border border-white/25 text-white hover:bg-white/20 font-bold"
              >
                {secondaryCtaLabel}
              </Link>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Main Page Component ─────────────────────────────────────────────────────

export default function CursosPage() {
  const heroPage = useCmsV2Page("courses");
  const fallbackHero = (heroPage?.blocks?.hero?.parsed as Record<string, unknown> | undefined) ?? null;
  const fallbackFeed = (heroPage?.blocks?.feed?.parsed as Record<string, unknown> | undefined) ?? null;

  const [courses, setCourses] = useState<PublicCourse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchCourses = useCallback(() => {
    const ctrl = new AbortController();
    setLoading(true);
    setError(false);

    apiFetch<PublicCourse[]>(`/public/courses?site_key=${encodeURIComponent(SITE_KEY)}`, {
      signal: ctrl.signal,
      silent: true,
    })
      .then((data) => {
        setCourses(Array.isArray(data) ? data : []);
        setError(false);
        setLoading(false);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        console.error("Error fetching courses:", err);
        setError(true);
        setCourses([]);
        setLoading(false);
      });

    return () => ctrl.abort();
  }, []);

  useEffect(() => {
    const cancel = fetchCourses();
    return () => {
      cancel();
    };
  }, [fetchCourses]);

  // Secciones ordenadas y filtradas según configuración en CMS
  const visibleSections = useMemo(() => {
    return (heroPage?.sections || [])
      .filter((s) => s.is_visible !== false && s.status !== "archived")
      .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  }, [heroPage?.sections]);

  const hasModularSections = visibleSections.length > 0;

  return (
    <main className="min-h-screen bg-site-background pt-[88px] pb-8 overflow-hidden">
      {hasModularSections ? (
        visibleSections.map((section) => {
          switch (section.section_key) {
            case "hero":
              return (
                <CursosHeroSection
                  key={section.id || "hero"}
                  section={section}
                  fallbackHero={fallbackHero}
                  courses={courses}
                />
              );

            case "feed":
            case "courses_catalog":
            case "catalog":
              return (
                <CursosCatalogSection
                  key={section.id || "feed"}
                  section={section}
                  fallbackFeed={fallbackFeed}
                  courses={courses}
                  loading={loading}
                  error={error}
                  onRetry={fetchCourses}
                />
              );

            case "cta":
              return (
                <CursosCtaSection
                  key={section.id || "cta"}
                  section={section}
                  fallbackFeed={fallbackFeed}
                />
              );

            default:
              if (section.type === "hero_banner" || section.type === "hero") {
                return (
                  <CursosHeroSection
                    key={section.id}
                    section={section}
                    fallbackHero={fallbackHero}
                    courses={courses}
                  />
                );
              }
              if (section.type === "catalog_grid" || section.type === "feed") {
                return (
                  <CursosCatalogSection
                    key={section.id}
                    section={section}
                    fallbackFeed={fallbackFeed}
                    courses={courses}
                    loading={loading}
                    error={error}
                    onRetry={fetchCourses}
                  />
                );
              }
              if (section.type === "cta_banner" || section.type === "cta") {
                return (
                  <CursosCtaSection
                    key={section.id}
                    section={section}
                    fallbackFeed={fallbackFeed}
                  />
                );
              }
              return null;
          }
        })
      ) : (
        /* Fallback si no hay secciones en BD */
        <>
          <CursosHeroSection fallbackHero={fallbackHero} courses={courses} />
          <CursosCatalogSection
            fallbackFeed={fallbackFeed}
            courses={courses}
            loading={loading}
            error={error}
            onRetry={fetchCourses}
          />
          <CursosCtaSection fallbackFeed={fallbackFeed} />
        </>
      )}
    </main>
  );
}

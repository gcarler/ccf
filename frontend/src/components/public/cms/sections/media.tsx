"use client";

import { CmsSection } from "@/types/cms-v2";
import type {
  GalleryProps, EmbedProps, ImageTextProps, VideoGridProps, EventsCalendarProps, LocationsListProps, CourseGridProps, BookShopProps, FeedProps,
} from "@/types/cms-section-props";
import OptimizedImage from "@/components/ui/OptimizedImage";
import Link from "next/link";
import { asItems, asProps, val } from "./shared";

export function GallerySection({ section }: { section: CmsSection<"gallery"> }) {
  const props: GalleryProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const body = val(p, "body", "");
  const imageUrl = val(p, "image_url", "");
  const imageAlt = val(p, "image_alt", title || "Imagen");
  const items = asItems(p) as Array<{ url?: string; alt?: string; caption?: string }>;

  const images = items.length > 0
    ? items.map((item) => ({ url: item.url || "", alt: item.alt || "", caption: item.caption || "" }))
    : imageUrl
    ? [{ url: imageUrl, alt: imageAlt, caption: "" }]
    : [];

  if (images.length === 0) return null;

  const isGrid = images.length > 1;

  return (
    <section className="ccf-section-panel overflow-hidden" style={{ background: "var(--site-surface-container-low)" }}>
      {isGrid ? (
        <div className={`grid gap-1 ${images.length === 2 ? "grid-cols-2" : images.length === 3 ? "grid-cols-3" : "grid-cols-2 md:grid-cols-4"}`}>
          {images.map((img, i) => (
            <div key={i} className="relative aspect-square group overflow-hidden">
              <OptimizedImage src={img.url} alt={img.alt} fill sizes="(max-width: 768px) 50vw, 25vw" className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" />
              {img.caption && (
                <div className="absolute inset-x-0 bottom-0 p-3 opacity-0 group-hover:opacity-100 transition-opacity" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.7), transparent)" }}>
                  <p className="text-xs text-white font-medium">{img.caption}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <OptimizedImage src={images[0].url} alt={images[0].alt} fill sizes="100vw" className="w-full max-h-[480px] object-cover" />
      )}
      {(title || body) && (
        <div className="p-6">
          {title && <h3 className="text-xl font-bold" style={{ color: "var(--site-on-surface)" }}>{title}</h3>}
          {body && <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
        </div>
      )}
    </section>
  );
}

// ─── FAQ ───────────────────────────────────────────────────────────────────────

export function EmbedSection({ section }: { section: CmsSection<"embed"> }) {
  const props: EmbedProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const body = val(p, "body", "");
  const embedUrl = val(p, "embed_url", "");

  // Google Photos bloquea la incrustación con x-frame-options: SAMEORIGIN.
  // Renderizar un CTA que abre el álbum en nueva pestaña.
  const isGooglePhotos = /photos\.app\.goo\.gl|photos\.google\.com/.test(embedUrl);

  return (
    <section className="ccf-section-panel p-7 md:p-10" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h3 className="text-xl font-bold mb-3" style={{ color: "var(--site-on-surface)" }}>{title}</h3>}
      {body && <p className="mb-4 text-sm leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
      {embedUrl ? (
        isGooglePhotos ? (
          <a
            href={embedUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-lg transition-transform hover:scale-105"
            style={{ background: "var(--site-cta-gradient)" }}
          >
            Ver galería de fotos
          </a>
        ) : (
          <div className="aspect-video rounded-xl overflow-hidden" style={{ background: "var(--site-surface-container)" }}>
            <iframe title={title} src={embedUrl} className="w-full h-full border-0" allowFullScreen />
          </div>
        )
      ) : (
        <div className="aspect-video rounded-xl flex items-center justify-center text-sm" style={{ background: "var(--site-surface-container)", color: "var(--site-on-surface-variant)" }}>
          Sin URL de embed configurada
        </div>
      )}
    </section>
  );
}

// ─── Testimonials ──────────────────────────────────────────────────────────────

export function ImageTextSection({ section }: { section: CmsSection<"image_text"> }) {
  const props: ImageTextProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const body = val(p, "body", "");
  const imageUrl = val(p, "image_url", "");
  const imageAlt = val(p, "image_alt", title);
  const ctaLabel = val(p, "cta_label", "");
  const ctaHref = val(p, "cta_href", "/");
  const side = val(p, "image_side", "right"); // "left" | "right"

  const textCol = (
    <div className="flex flex-col justify-center gap-5 py-4 md:py-0">
      {title && <h2 className="text-2xl md:text-4xl font-black tracking-tight leading-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {body && <p className="text-base leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
      {ctaLabel && (
        <Link
          href={ctaHref}
          className="inline-flex self-start items-center gap-2 rounded-full px-5 py-2.5 text-sm font-bold uppercase tracking-widest text-white transition-transform hover:scale-105"
          style={{ background: "var(--site-cta-gradient)" }}
        >
          {ctaLabel}
        </Link>
      )}
    </div>
  );

  const imgCol = imageUrl ? (
    <div className="relative rounded-xl overflow-hidden aspect-[4/3]">
      <OptimizedImage src={imageUrl} alt={imageAlt} fill sizes="(max-width: 768px) 100vw, 50vw" className="w-full h-full object-cover" />
    </div>
  ) : null;

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12 items-center">
        {side === "left" && imgCol}
        {textCol}
        {side !== "left" && imgCol}
      </div>
    </section>
  );
}

// ─── Timeline ──────────────────────────────────────────────────────────────────

export function VideoGridSection({ section }: { section: CmsSection<"video_grid"> }) {
  const props: VideoGridProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Prédicas & Mensajes");
  const subtitle = val(p, "subtitle", "");
  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {subtitle && <p className="mt-3 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      <div className="mt-6 rounded-xl p-8 text-center border-2 border-dashed" style={{ borderColor: "var(--site-outline-variant)" }}>
        <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
          La biblioteca de videos se renderiza desde el canal de YouTube.
        </p>
      </div>
    </section>
  );
}

// ─── Locations List (config-only shell; data comes from sedes API) ─────────────

export function EventsCalendarSection({ section }: { section: CmsSection<"events_calendar"> }) {
  const props: EventsCalendarProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Próximos Eventos");
  const subtitle = val(p, "subtitle", "");
  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {subtitle && <p className="mt-3 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      <div className="mt-6 rounded-xl p-8 text-center border-2 border-dashed" style={{ borderColor: "var(--site-outline-variant)" }}>
        <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
          El calendario de eventos se renderiza desde el módulo de eventos.
        </p>
      </div>
    </section>
  );
}

// ─── Video Grid (config-only shell; data comes from YouTube API) ───────────────

export function LocationsListSection({ section }: { section: CmsSection<"locations_list"> }) {
  const props: LocationsListProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Nuestras Sedes");
  const subtitle = val(p, "subtitle", "");
  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {subtitle && <p className="mt-3 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      <div className="mt-6 rounded-xl p-8 text-center border-2 border-dashed" style={{ borderColor: "var(--site-outline-variant)" }}>
        <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
          El listado de sedes se renderiza desde el módulo de ubicaciones.
        </p>
      </div>
    </section>
  );
}

// ─── Contact Form ──────────────────────────────────────────────────────────────

export function CourseGridSection({ section }: { section: CmsSection<"course_grid"> }) {
  const props: CourseGridProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Cursos & Academia");
  const subtitle = val(p, "subtitle", "");
  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {subtitle && <p className="mt-3 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      <div className="mt-6 rounded-xl p-8 text-center border-2 border-dashed" style={{ borderColor: "var(--site-outline-variant)" }}>
        <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
          El listado de cursos se renderiza desde la Academia.
        </p>
      </div>
    </section>
  );
}

// ─── Book Shop (config-only shell; data comes from academy API) ─────────────────

export function BookShopSection({ section }: { section: CmsSection<"book_shop"> }) {
  const props: BookShopProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Nuestra Librería");
  const subtitle = val(p, "subtitle", "");
  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {subtitle && <p className="mt-3 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      <div className="mt-6 rounded-xl p-8 text-center border-2 border-dashed" style={{ borderColor: "var(--site-outline-variant)" }}>
        <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
          La librería se renderiza desde la Academia.
        </p>
      </div>
    </section>
  );
}

// ─── Feed Section ──────────────────────────────────────────────────────────────
// Renderiza el tipo "feed" usado en home, sermons, courses, testimonials, pastors, events, locations

export function FeedSection({ section }: { section: CmsSection<"feed"> }) {
  const props: FeedProps = section.props_json ?? {};
  const p = asProps(props);

  // Detectar qué variante de feed es según los campos presentes
  const isHomeFeed = p.featured_card || p.cards;
  const isSermonsFeed = p.content;
  const isCoursesFeed = p.courses_title || p.hero_image_url || p.cta_images;
  const isTestimonialsFeed = p.hero_badge && p.hero_title_lead;
  const isEventsFeed = p.empty_title && p.no_events_title;
  const isPastorsFeed = p.hero_badge && p.hero_title && p.card_cta;
  const isLocationsFeed = p.section_key === "feed" && !p.featured_card && !p.content && !p.courses_title && !p.hero_badge;

  // Home feed: featured_card + 3 cards + newsletter
  if (isHomeFeed) {
    const eyebrow = val(p, "eyebrow", "");
    const sectionTitle = val(p, "section_title", "");
    const sectionDescription = val(p, "section_description", "");
    const featuredCard = p.featured_card as Record<string, unknown> | undefined;
    const cards = p.cards as Array<Record<string, unknown>> | undefined;
    const activitiesEyebrow = val(p, "activities_eyebrow", "");
    const activitiesTitle = val(p, "activities_title", "");
    const activitiesViewAll = val(p, "activities_view_all", "");
    const activitiesEmpty = val(p, "activities_empty", "");
    const newsletterEyebrow = val(p, "newsletter_eyebrow", "");
    const newsletterTitle = val(p, "newsletter_title", "");
    const newsletterDescription = val(p, "newsletter_description", "");
    const newsletterPlaceholder = val(p, "newsletter_placeholder", "");
    const newsletterSubmit = val(p, "newsletter_submit", "");

    return (
      <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
        {eyebrow && <span className="ccf-kicker inline-flex items-center gap-2 text-xs uppercase mb-3" style={{ color: "var(--site-primary)" }}>{eyebrow}</span>}
        {sectionTitle && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{sectionTitle}</h2>}
        {sectionDescription && <p className="mt-3 max-w-2xl" style={{ color: "var(--site-on-surface-variant)" }}>{sectionDescription}</p>}

        {featuredCard && (
          <Link href={val(featuredCard, "href", "/")} className="block my-8 rounded-xl overflow-hidden group" style={{ background: "var(--site-surface-container)" }}>
            <div className="relative aspect-[16/9]">
              {val(featuredCard, "img", "") && (
                <OptimizedImage src={val(featuredCard, "img", "")} alt={val(featuredCard, "alt", "")} fill sizes="100vw" className="object-cover transition-transform duration-700 group-hover:scale-105" />
              )}
              <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 60%)" }} />
              <div className="absolute bottom-0 p-6 md:p-8 w-full">
                <span className="inline-block px-4 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wide mb-3" style={{ background: "var(--site-card-highlight)", color: "var(--site-primary)" }}>
                  {val(featuredCard, "title", "")}
                </span>
                <p className="text-base md:text-lg font-medium text-white mb-3 max-w-xl">{val(featuredCard, "desc", "")}</p>
                <span className="inline-flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-white">{val(featuredCard, "cta", "Ver más")} →</span>
              </div>
            </div>
          </Link>
        )}

        {cards && cards.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {cards.slice(0, 3).map((card, i) => (
              <Link key={i} href={val(card, "href", "#")} className="rounded-xl overflow-hidden group transition-transform hover:-translate-y-1 hover:shadow-lg" style={{ background: "var(--site-surface-container)" }}>
                {val(card, "img", "") && (
                  <div className="relative aspect-[4/3]">
                    <OptimizedImage src={val(card, "img", "")} alt={val(card, "alt", "")} fill sizes="(max-width: 768px) 50vw, 33vw" className="object-cover transition-transform duration-500 group-hover:scale-105" />
                  </div>
                )}
                <div className="p-5 flex flex-col gap-3">
                  <h3 className="font-bold" style={{ color: "var(--site-on-surface)" }}>{val(card, "title", `Tarjeta ${i + 1}`)}</h3>
                  {val(card, "desc", "") && <p className="text-sm leading-relaxed flex-1" style={{ color: "var(--site-on-surface-variant)" }}>{val(card, "desc", "")}</p>}
                  {val(card, "href", "") && <span className="text-xs font-bold uppercase tracking-widest mt-auto" style={{ color: "var(--site-primary)" }}>Ver más →</span>}
                </div>
              </Link>
            ))}
          </div>
        )}

        {(activitiesTitle || newsletterTitle) && <hr className="my-12 border-[hsl(var(--border))]" />}

        {activitiesTitle && (
          <div>
            {activitiesEyebrow && <span className="ccf-kicker inline-flex items-center gap-2 text-xs uppercase mb-2" style={{ color: "var(--site-primary)" }}>{activitiesEyebrow}</span>}
            <h3 className="text-xl md:text-2xl font-black tracking-tight mb-4" style={{ color: "var(--site-on-surface)" }}>{activitiesTitle}</h3>
            <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>{activitiesEmpty}</p>
            {activitiesViewAll && (
              <Link href="/eventos" className="inline-flex mt-4 items-center gap-2 text-sm font-bold uppercase tracking-widest" style={{ color: "var(--site-primary)" }}>
                {activitiesViewAll}
              </Link>
            )}
          </div>
        )}

        {newsletterTitle && (
          <div className="mt-8 max-w-md">
            {newsletterEyebrow && <span className="ccf-kicker inline-flex items-center gap-2 text-xs uppercase mb-2" style={{ color: "var(--site-primary)" }}>{newsletterEyebrow}</span>}
            <h3 className="text-xl md:text-2xl font-black tracking-tight mb-2" style={{ color: "var(--site-on-surface)" }}>{newsletterTitle}</h3>
            {newsletterDescription && <p className="mt-2 text-sm" style={{ color: "var(--site-on-surface-variant)" }}>{newsletterDescription}</p>}
            <form className="mt-4 flex gap-2" onSubmit={(e) => e.preventDefault()}>
              <input
                type="email"
                placeholder={newsletterPlaceholder}
                className="flex-1 rounded-xl px-4 py-3 text-sm border"
                style={{ borderColor: "var(--site-outline)", background: "var(--site-surface)", color: "var(--site-on-surface)" }}
              />
              <button type="submit" className="px-5 py-3 text-sm font-bold uppercase tracking-widest text-white" style={{ background: "var(--site-cta-gradient)" }}>
                {newsletterSubmit}
              </button>
            </form>
          </div>
        )}
      </section>
    );
  }

  // Sermons feed: YouTube video grid with search
  if (isSermonsFeed) {
    const contentStr = val(p, "content", "{}");
    let content: Record<string, unknown> = {};
    try { content = JSON.parse(contentStr); } catch {}
    const heroEyebrow = val(content, "hero_eyebrow", "");
    const heroTitleLead = val(content, "hero_title_lead", "");
    const heroTitleAccent = val(content, "hero_title_accent", "");
    const heroDescription = val(content, "hero_description", "");
    const ctaLabel = val(content, "cta_label", "");

    return (
      <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
        {heroEyebrow && <span className="ccf-kicker inline-flex items-center gap-2 text-xs uppercase mb-3" style={{ color: "var(--site-primary)" }}>{heroEyebrow}</span>}
        {heroTitleLead && (
          <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>
            {heroTitleLead}{" "}
            {heroTitleAccent && (
              <span style={{ background: "var(--site-hero-accent-1)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                {heroTitleAccent}
              </span>
            )}
          </h2>
        )}
        {heroDescription && <p className="mt-3 max-w-2xl" style={{ color: "var(--site-on-surface-variant)" }}>{heroDescription}</p>}
        <div className="mt-8 rounded-xl p-8 text-center border-2 border-dashed" style={{ borderColor: "var(--site-outline-variant)" }}>
          <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
            Biblioteca de videos desde YouTube — configurar integración para renderizar grid completo.
          </p>
          {ctaLabel && (
            <Link href="https://youtube.com/@comunidadccf" target="_blank" rel="noopener noreferrer" className="inline-flex mt-4 items-center gap-2 text-sm font-bold uppercase tracking-widest text-white" style={{ background: "var(--site-cta-gradient)" }}>
              {ctaLabel}
            </Link>
          )}
        </div>
      </section>
    );
  }

  // Courses feed: featured course + grid
  if (isCoursesFeed) {
    const heroImageUrl = val(p, "hero_image_url", "");
    const coursesTitle = val(p, "courses_title", "");
    const coursesDescription = val(p, "courses_description", "");
    const emptyTitle = val(p, "empty_title", "");
    const emptyDescription = val(p, "empty_description", "");
    const ctaImages = p.cta_images as Array<{ src?: string; alt?: string }> | undefined;

    return (
      <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
        {heroImageUrl && coursesTitle && (
          <div className="relative rounded-xl overflow-hidden mb-10 aspect-[16/9]">
            <OptimizedImage src={heroImageUrl} alt={coursesTitle} fill sizes="100vw" className="object-cover" />
            <div className="absolute inset-0" style={{ background: "linear-gradient(to top, var(--site-surface-container-lowest) 0%, transparent 60%)" }} />
            <div className="absolute bottom-0 p-6 md:p-8 w-full">
              <h2 className="text-2xl md:text-3xl font-black text-white mb-3">{coursesTitle}</h2>
              {coursesDescription && <p className="text-white/90 max-w-xl">{coursesDescription}</p>}
            </div>
          </div>
        )}
        {ctaImages && ctaImages.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {ctaImages.slice(0, 3).map((img, i) => (
              <div key={i} className="relative aspect-[4/3] rounded-xl overflow-hidden group">
                <OptimizedImage src={val(img, "src", "")} alt={val(img, `alt`, `Curso ${i + 1}`)} fill sizes="(max-width: 768px) 50vw, 33vw" className="object-cover transition-transform duration-500 group-hover:scale-105" />
              </div>
            ))}
          </div>
        )}
        {!ctaImages && (
          <div className="rounded-lg p-8 text-center" style={{ background: "var(--site-surface-container-low)" }}>
            {emptyTitle && <h3 className="text-xl font-bold mb-2">{emptyTitle}</h3>}
            {emptyDescription && <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>{emptyDescription}</p>}
          </div>
        )}
      </section>
    );
  }

  // Testimonials feed: search + grid
  if (isTestimonialsFeed) {
    const heroBadge = val(p, "hero_badge", "");
    const heroTitleLead = val(p, "hero_title_lead", "");
    const heroTitleAccent = val(p, "hero_title_accent", "");
    const heroDescription = val(p, "hero_description", "");
    const ctaLabel = val(p, "cta_label", "");

    return (
      <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
        {heroBadge && <span className="ccf-kicker inline-flex items-center gap-2 text-xs uppercase mb-3" style={{ color: "var(--site-primary)" }}>{heroBadge}</span>}
        {heroTitleLead && (
          <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>
            {heroTitleLead}{" "}
            {heroTitleAccent && (
              <span style={{ background: "var(--site-hero-accent-1)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                {heroTitleAccent}
              </span>
            )}
          </h2>
        )}
        {heroDescription && <p className="mt-3 max-w-2xl" style={{ color: "var(--site-on-surface-variant)" }}>{heroDescription}</p>}
        <div className="mt-8 rounded-xl p-8 text-center border-2 border-dashed" style={{ borderColor: "var(--site-outline-variant)" }}>
          <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
            Testimonios se renderizan desde el módulo de testimonios — configurar API para grid completo.
          </p>
          {ctaLabel && (
            <button className="inline-flex mt-4 items-center gap-2 text-sm font-bold uppercase tracking-widest text-white" style={{ background: "var(--site-cta-gradient)" }}>
              {ctaLabel}
            </button>
          )}
        </div>
      </section>
    );
  }

  // Events feed
  if (isEventsFeed) {
    const emptyTitle = val(p, "empty_title", "");
    const emptyDescription = val(p, "empty_description", "");
    const calendarTitle = val(p, "calendar_title", "");
    const calendarDescription = val(p, "calendar_description", "");

    return (
      <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
        <div className="rounded-xl p-8 text-center border-2 border-dashed" style={{ borderColor: "var(--site-outline-variant)" }}>
          <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
            {emptyTitle && <p className="font-bold mb-2">{emptyTitle}</p>}
            {emptyDescription}
          </p>
          {calendarTitle && (
            <div className="mt-8">
              <h3 className="text-xl font-bold mb-2">{calendarTitle}</h3>
              {calendarDescription && <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>{calendarDescription}</p>}
            </div>
          )}
        </div>
      </section>
    );
  }

  // Pastors feed
  if (isPastorsFeed) {
    const heroBadge = val(p, "hero_badge", "");
    const heroTitle = val(p, "hero_title", "");
    const heroDescription = val(p, "hero_description", "");

    return (
      <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
        {heroBadge && <span className="ccf-kicker inline-flex items-center gap-2 text-xs uppercase mb-3" style={{ color: "var(--site-primary)" }}>{heroBadge}</span>}
        {heroTitle && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{heroTitle}</h2>}
        {heroDescription && <p className="mt-3 max-w-2xl" style={{ color: "var(--site-on-surface-variant)" }}>{heroDescription}</p>}
        <div className="mt-8 rounded-xl p-8 text-center border-2 border-dashed" style={{ borderColor: "var(--site-outline-variant)" }}>
          <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
            Equipo pastoral se renderiza desde el módulo de pastores — configurar API para grid completo.
          </p>
        </div>
      </section>
    );
  }

  // Locations feed (empty, shell only)
  if (isLocationsFeed) {
    return (
      <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
        <div className="rounded-xl p-8 text-center border-2 border-dashed" style={{ borderColor: "var(--site-outline-variant)" }}>
          <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
            Listado de sedes se renderiza desde el módulo de ubicaciones.
          </p>
        </div>
      </section>
    );
  }

  // Generic fallback
  const title = val(p, "title", "");
  const body = val(p, "body", "");
  const items = asItems(p);

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-4" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {body && <p className="mb-6" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
      {items.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item, i) => (
            <div key={i} className="rounded-xl p-4 border" style={{ borderColor: "var(--site-outline)", background: "var(--site-surface-container)" }}>
              <pre className="text-xs overflow-auto">{JSON.stringify(item, null, 2)}</pre>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ─── Testimonials Masonry (config-only shell; data comes from testimonials API) ─

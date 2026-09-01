"use client";

import { CmsSection } from "@/types/cms-v2";
import type {
  GalleryProps, EmbedProps, ImageTextProps, VideoGridProps, EventsCalendarProps, LocationsListProps, CourseGridProps, BookShopProps, FeedProps,
} from "@/types/cms-section-props";
import OptimizedImage from "@/components/ui/OptimizedImage";
import Link from "next/link";
import React, { useState } from "react";
import { apiFetch } from "@/lib/http";
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
  const title = val(p, "title");
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
  const title = val(p, "title");
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
  const title = val(p, "title");
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
  const title = val(p, "title");
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
  const title = val(p, "title");
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
//
// Normalización previa: los seeders históricos guardan los feeds de sermons /
// events / pastors / testimonials envueltos como ``{content: "<json-string>"}``
// (helper ``_content_json``) y ``ensure_public_cms_pastors`` además reparte los
// campos al nivel superior. Se desempaqueta ``content`` (string JSON u objeto)
// y se hace merge con el nivel superior ANTES de detectar la variante, para que
// la detección no dependa de la forma de serialización. Por eso la clave
// ``content`` NO se usa como discriminante: está presente en casi todos los
// feeds sembrados y hacía que events/pastors/testimonials cayeran en la
// variante sermons.

function isLocationItem(item: unknown): item is Record<string, unknown> {
  if (!item || typeof item !== "object") return false;
  const record = item as Record<string, unknown>;
  const hasName = typeof record.name === "string" && record.name.trim().length > 0;
  const hasAddress = typeof record.address === "string" && record.address.trim().length > 0;
  return hasName || hasAddress;
}

function unwrapFeedProps(raw: FeedProps | Array<Record<string, unknown>>): Record<string, unknown> {
  if (Array.isArray(raw)) {
    // Feed de sedes sembrado como lista plana de items (ccf_locations_feed).
    return { items: raw };
  }
  const props = { ...(raw as Record<string, unknown>) };
  const content = props.content;
  if (typeof content === "string") {
    try {
      const parsed: unknown = JSON.parse(content);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        // Merge: los campos del nivel superior ganan sobre los internos
        // (``ensure_public_cms_pastors`` reparte `**feed` al nivel superior).
        return { ...(parsed as Record<string, unknown>), ...props };
      }
    } catch {
      // content no es JSON válido: se ignora y se usa el nivel superior.
    }
  } else if (content && typeof content === "object" && !Array.isArray(content)) {
    return { ...(content as Record<string, unknown>), ...props };
  }
  return props;
}

export function FeedSection({ section }: { section: CmsSection<"feed"> }) {
  const rawProps = section.props_json ?? {};
  const p = unwrapFeedProps(rawProps as FeedProps | Array<Record<string, unknown>>);

  // Newsletter (variante home): envío real al endpoint público de suscripción
  // (POST /api/cms/v2/public/subscribe, rate-limited en backend). Se muestra
  // éxito con los textos configurados o error inline para reintentar.
  const [nlEmail, setNlEmail] = useState("");
  const [nlStatus, setNlStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  const handleNewsletterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nlEmail.trim()) return;
    setNlStatus("sending");
    try {
      await apiFetch("/cms/v2/public/subscribe", {
        method: "POST",
        body: { site_key: "ccf", email: nlEmail.trim() },
        silent: true,
      });
      setNlStatus("sent");
      setNlEmail("");
    } catch {
      setNlStatus("error");
    }
  };

  // Detectar qué variante de feed es según los campos presentes, en orden de
  // especificidad (cada discriminante es exclusivo de una variante).
  const isCoursesFeed = Boolean(p.courses_title || p.hero_image_url || p.cta_images);
  // newsletter_title también activa la variante home: un feed configurado solo
  // con el bloque del boletín debe renderizar el formulario. Sin colisiones:
  // courses usa newsletter_success_toast (no newsletter_title) y ningún otro
  // discriminante comparte este campo.
  const isHomeFeed = Boolean(p.featured_card || p.cards || p.newsletter_title);
  const isSermonsFeed = Boolean(p.hero_eyebrow || (p.hero_title_lead && !p.hero_badge));
  const isTestimonialsFeed = Boolean(p.hero_badge && p.hero_title_lead);
  const isPastorsFeed = Boolean(p.hero_badge && p.hero_title && p.card_cta);
  const isEventsFeed = Boolean(p.empty_title && p.no_events_title);
  const isLocationsFeed =
    Array.isArray(section.props_json) ||
    (Array.isArray(p.items) && p.items.length > 0 && isLocationItem(p.items[0]));

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
    const newsletterSuccessTitle = val(p, "newsletter_success_title", "");
    const newsletterSuccessDesc = val(p, "newsletter_success_desc", "");

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
                <span className="inline-flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-white">{val(featuredCard, "cta")} →</span>
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
                  <h3 className="font-bold" style={{ color: "var(--site-on-surface)" }}>{val(card, "title")}</h3>
                  {val(card, "desc", "") && <p className="text-sm leading-relaxed flex-1" style={{ color: "var(--site-on-surface-variant)" }}>{val(card, "desc", "")}</p>}
                  {val(card, "href", "") && val(card, "cta", "") && <span className="text-xs font-bold uppercase tracking-widest mt-auto" style={{ color: "var(--site-primary)" }}>{val(card, "cta")} →</span>}
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
        )}            {newsletterTitle && (
          <div className="mt-8 max-w-md">
            {newsletterEyebrow && <span className="ccf-kicker inline-flex items-center gap-2 text-xs uppercase mb-2" style={{ color: "var(--site-primary)" }}>{newsletterEyebrow}</span>}
            <h3 className="text-xl md:text-2xl font-black tracking-tight mb-2" style={{ color: "var(--site-on-surface)" }}>{newsletterTitle}</h3>
            {newsletterDescription && <p className="mt-2 text-sm" style={{ color: "var(--site-on-surface-variant)" }}>{newsletterDescription}</p>}
            {nlStatus === "sent" ? (
              <div aria-live="polite" className="mt-4 rounded-xl p-5 border" style={{ borderColor: "var(--site-outline)", background: "var(--site-surface-container)" }}>
                <p className="font-bold" style={{ color: "var(--site-on-surface)" }}>
                  {newsletterSuccessTitle || "¡Gracias por suscribirte!"}
                </p>
                {newsletterSuccessDesc && (
                  <p className="mt-1 text-sm" style={{ color: "var(--site-on-surface-variant)" }}>{newsletterSuccessDesc}</p>
                )}
              </div>
            ) : (
              <>
                <form className="mt-4 flex flex-col sm:flex-row gap-2" onSubmit={handleNewsletterSubmit}>
                  <input
                    type="email"
                    value={nlEmail}
                    onChange={(e) => {
                      setNlEmail(e.target.value);
                      if (nlStatus === "error") setNlStatus("idle");
                    }}
                    placeholder={newsletterPlaceholder}
                    required
                    disabled={nlStatus === "sending"}
                    aria-label="Correo electrónico para el boletín"
                    className="flex-1 min-w-0 rounded-xl px-4 py-3 text-sm border outline-none disabled:opacity-60"
                    style={{ borderColor: "var(--site-outline)", background: "var(--site-surface)", color: "var(--site-on-surface)" }}
                  />
                  <button
                    type="submit"
                    disabled={nlStatus === "sending"}
                    className="px-5 py-3 text-sm font-bold uppercase tracking-widest text-white rounded-xl disabled:opacity-60 transition-opacity hover:opacity-90"
                    style={{ background: "var(--site-cta-gradient)" }}
                  >
                    {nlStatus === "sending" ? "Enviando..." : newsletterSubmit}
                  </button>
                </form>
                {nlStatus === "error" && (
                  <p aria-live="polite" className="mt-3 text-sm font-semibold text-[hsl(var(--destructive))]" role="alert">
                    No se pudo suscribir. Intenta de nuevo.
                  </p>
                )}
              </>
            )}
          </div>
        )}
      </section>
    );
  }

  // Sermons feed: YouTube video grid with search
  if (isSermonsFeed) {
    // Las props ya vienen normalizadas (unwrap de `content`); se leen los
    // campos hero directamente del nivel superior.
    const heroEyebrow = val(p, "hero_eyebrow", "");
    const heroTitleLead = val(p, "hero_title_lead", "");
    const heroTitleAccent = val(p, "hero_title_accent", "");
    const heroDescription = val(p, "hero_description", "");
    const ctaLabel = val(p, "cta_label", "");
    const channelUrl = val(p, "youtube_channel_url");

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
            <Link href={channelUrl} target="_blank" rel="noopener noreferrer" className="inline-flex mt-4 items-center gap-2 text-sm font-bold uppercase tracking-widest text-white" style={{ background: "var(--site-cta-gradient)" }}>
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
                <OptimizedImage src={val(img, "src")} alt={val(img, "alt")} fill sizes="(max-width: 768px) 50vw, 33vw" className="object-cover transition-transform duration-500 group-hover:scale-105" />
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
          {emptyTitle && <p className="text-sm font-bold mb-2" style={{ color: "var(--site-on-surface)" }}>{emptyTitle}</p>}
          {emptyDescription && <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>{emptyDescription}</p>}
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

  // Locations feed: lista de sedes (props puede ser un array plano o `items`)
  if (isLocationsFeed) {
    const locations = Array.isArray(p.items) ? (p.items as Array<Record<string, unknown>>) : [];
    return (
      <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {locations.map((loc, i) => (
            <div key={i} className="rounded-xl p-6 border" style={{ borderColor: "var(--site-outline)", background: "var(--site-surface-container)" }}>
              <h2 className="text-lg font-bold mb-2" style={{ color: "var(--site-on-surface)" }}>{val(loc, "name")}</h2>
              {val(loc, "address", "") && <p className="text-sm mb-1" style={{ color: "var(--site-on-surface-variant)" }}>{val(loc, "address", "")}</p>}
              {val(loc, "phone", "") && <p className="text-sm mb-1" style={{ color: "var(--site-on-surface-variant)" }}>{val(loc, "phone", "")}</p>}
              {val(loc, "schedule", "") && <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>{val(loc, "schedule", "")}</p>}
            </div>
          ))}
        </div>
      </section>
    );
  }

  // Pastors grid feed: sección section_key="pastors" (type feed) con la lista real
  // del equipo pastoral (ensure_public_cms_pastors) — sin hero, solo el grid.
  if (Array.isArray(p.pastors) && p.pastors.length > 0) {
    const pastors = p.pastors as Array<Record<string, unknown>>;
    return (
      <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {pastors.map((pastor, i) => (
            <div key={val(pastor, "slug") || i} className="rounded-xl overflow-hidden border" style={{ borderColor: "var(--site-outline)", background: "var(--site-surface-container)" }}>
              {val(pastor, "image", "") && (
                <div className="relative aspect-[4/3]">
                  <OptimizedImage src={val(pastor, "image")} alt={val(pastor, "name")} fill sizes="(max-width: 768px) 50vw, 33vw" className="object-cover object-top" />
                </div>
              )}
              <div className="p-5">
                <h2 className="font-bold" style={{ color: "var(--site-on-surface)" }}>{val(pastor, "name")}</h2>
                {val(pastor, "role", "") && <p className="text-xs font-bold uppercase tracking-widest mt-1" style={{ color: "var(--site-primary)" }}>{val(pastor, "role", "")}</p>}
                {val(pastor, "story", "") && <p className="mt-3 text-sm leading-relaxed line-clamp-3" style={{ color: "var(--site-on-surface-variant)" }}>{val(pastor, "story", "")}</p>}
              </div>
            </div>
          ))}
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
      {items.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item, i) => (
            <div key={i} className="rounded-xl p-4 border" style={{ borderColor: "var(--site-outline)", background: "var(--site-surface-container)" }}>
              {val(item, "title", "") && <h3 className="text-sm font-bold mb-1" style={{ color: "var(--site-on-surface)" }}>{val(item, "title", "")}</h3>}
              {(val(item, "body", "") || val(item, "desc", "") || val(item, "description", "")) && (
                <p className="text-xs leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
                  {val(item, "body", "") || val(item, "desc", "") || val(item, "description", "")}
                </p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-center" style={{ color: "var(--site-on-surface-variant)" }}>
          Sección sin contenido configurado.
        </p>
      )}
    </section>
  );
}

// ─── Testimonials Masonry (config-only shell; data comes from testimonials API) ─

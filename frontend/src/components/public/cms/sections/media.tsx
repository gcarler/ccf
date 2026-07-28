"use client";

import { CmsSection } from "@/types/cms-v2";
import type {
  GalleryProps, EmbedProps, ImageTextProps, VideoGridProps, EventsCalendarProps, LocationsListProps, CourseGridProps, BookShopProps,
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

  return (
    <section className="ccf-section-panel p-7 md:p-10" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h3 className="text-xl font-bold mb-3" style={{ color: "var(--site-on-surface)" }}>{title}</h3>}
      {body && <p className="mb-4 text-sm leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
      {embedUrl ? (
        <div className="aspect-video rounded-xl overflow-hidden" style={{ background: "var(--site-surface-container)" }}>
          <iframe title={title} src={embedUrl} className="w-full h-full border-0" allowFullScreen />
        </div>
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

// ─── Testimonials Masonry (config-only shell; data comes from testimonials API) ─


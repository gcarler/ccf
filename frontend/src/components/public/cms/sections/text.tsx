"use client";

import { CmsSection } from "@/types/cms-v2";
import type {
  RichTextProps,
  RichTextColumnsProps,
  AboutProps,
  CardsProps,
  CtaBannerProps,
} from "@/types/cms-section-props";
import Link from "next/link";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { asItems, asProps, val } from "./shared";

export function RichTextSection({ section }: { section: CmsSection<"rich_text"> }) {
  const props: RichTextProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const body = val(p, "body", "");
  const ctaLabel = val(p, "cta_label", "");
  const ctaHref = val(p, "cta_href", "/");

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-4" style={{ color: "var(--site-on-surface)" }}>
          {title}
        </h2>
      )}
      {body && (
        <div className="prose prose-base max-w-3xl leading-relaxed whitespace-pre-line" style={{ color: "var(--site-on-surface-variant)" }}>
          {body}
        </div>
      )}
      {ctaLabel && ctaHref && (
        <Link
          href={ctaHref}
          className="inline-flex mt-6 items-center gap-2 text-sm font-bold uppercase tracking-widest transition-opacity hover:opacity-70"
          style={{ color: "var(--site-primary)" }}
        >
          {ctaLabel} →
        </Link>
      )}
    </section>
  );
}

// ─── Rich Text Columns ─────────────────────────────────────────────────────────

export function RichTextColumnsSection({ section }: { section: CmsSection<"rich_text_columns"> }) {
  const props: RichTextColumnsProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const body = val(p, "body", "");
  const body2 = val(p, "body_2", body);

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-6" style={{ color: "var(--site-on-surface)" }}>
          {title}
        </h2>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-10">
        <div className="leading-relaxed whitespace-pre-line text-base" style={{ color: "var(--site-on-surface-variant)" }}>
          {body}
        </div>
        <div className="leading-relaxed whitespace-pre-line text-base" style={{ color: "var(--site-on-surface-variant)" }}>
          {body2}
        </div>
      </div>
    </section>
  );
}

// ─── Cards ─────────────────────────────────────────────────────────────────────

export function CardsSection({ section }: { section: CmsSection<"cards"> }) {
  const props: CardsProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const body = val(p, "body", "");
  const items = asItems(p).slice(0, 9) as Array<{ title?: string; body?: string; href?: string; icon?: string }>;

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {(title || body) && (
        <div className="mb-10 md:mb-12">
          {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
          {body && <p className="mt-3 text-base max-w-2xl" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
        {items.map((card, i) => {
          const inner = (
            <>
              {card.icon && <span className="text-3xl">{card.icon}</span>}
              <h3 className="text-lg font-bold" style={{ color: "var(--site-on-surface)" }}>{card.title || `Tarjeta ${i + 1}`}</h3>
              {card.body && <p className="text-sm leading-relaxed flex-1" style={{ color: "var(--site-on-surface-variant)" }}>{card.body}</p>}
              {card.href && (
                <span className="text-xs font-bold uppercase tracking-widest mt-1" style={{ color: "var(--site-primary)" }}>
                  Ver más →
                </span>
              )}
            </>
          );
          const cls = `rounded-xl p-6 flex flex-col gap-3 ${card.href ? "transition-transform hover:-translate-y-1 hover:shadow-md" : ""}`;
          const sty = { background: "var(--site-surface-container)" };
          if (card.href) {
            return <Link key={i} href={card.href} className={cls} style={sty}>{inner}</Link>;
          }
          return <div key={i} className={cls} style={sty}>{inner}</div>;
        })}
      </div>
    </section>
  );
}

// ─── About Section ──────────────────────────────────────────────────────────────
// Renderiza la sección "about" de la página /nosotros con stats, visión, misión,
// fundadores, valores, cita y CTAs

export function AboutSection({ section }: { section: CmsSection<"about"> }) {
  const props: AboutProps = section.props_json ?? {};
  const p = asProps(props);

  const stats = p.stats as Array<{ value?: string; label?: string }> | undefined;
  const visionTitle = val(p, "vision_title", "");
  const visionText = val(p, "vision_text", "");
  const misionTitle = val(p, "mision_title", "");
  const misionText = val(p, "mision_text", "");
  const founderLabel = val(p, "founder_label", "");
  const founder1Name = val(p, "founder1_name", "");
  const founder1Role = val(p, "founder1_role", "");
  const founder1Image = val(p, "founder1_image", "");
  const founder2Name = val(p, "founder2_name", "");
  const founder2Role = val(p, "founder2_role", "");
  const founder2Image = val(p, "founder2_image", "");
  const founderBio = val(p, "founder_bio", "");
  const founderBio2 = val(p, "founder_bio2", "");
  const valoresTitle = val(p, "valores_title", "");
  const valores = p.valores as Array<{ num?: string; key?: string; title?: string; desc?: string }> | undefined;
  const quoteText = val(p, "quote_text", "");
  const quoteAuthor = val(p, "quote_author", "");
  const quoteSubtitle = val(p, "quote_subtitle", "");
  const ctaTitle = val(p, "cta_title", "");
  const ctaDesc = val(p, "cta_desc", "");
  const founderCtaTeam = val(p, "founder_cta_team", "");
  const founderCtaVisit = val(p, "founder_cta_visit", "");
  const valuesEyebrow = val(p, "values_eyebrow", "");
  const ctaViewSedes = val(p, "cta_view_sedes", "");
  const ctaViewEvents = val(p, "cta_view_events", "");

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {/* Stats */}
      {stats && stats.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-16">
          {stats.map((stat, i) => (
            <div key={i} className="text-center">
              <div className="text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>
                {stat.value}
              </div>
              <div className="text-sm mt-1" style={{ color: "var(--site-on-surface-variant)" }}>
                {stat.label}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Visión y Misión */}
      {(visionTitle || misionTitle) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
          {visionTitle && (
            <div className="p-6 rounded-xl" style={{ background: "var(--site-surface-container)" }}>
              <h3 className="text-xl font-bold mb-3" style={{ color: "var(--site-on-surface)" }}>{visionTitle}</h3>
              <div className="prose prose-sm" style={{ color: "var(--site-on-surface-variant)" }} dangerouslySetInnerHTML={{ __html: visionText }} />
            </div>
          )}
          {misionTitle && (
            <div className="p-6 rounded-xl" style={{ background: "var(--site-surface-container)" }}>
              <h3 className="text-xl font-bold mb-3" style={{ color: "var(--site-on-surface)" }}>{misionTitle}</h3>
              <div className="prose prose-sm" style={{ color: "var(--site-on-surface-variant)" }} dangerouslySetInnerHTML={{ __html: misionText }} />
            </div>
          )}
        </div>
      )}

      {/* Fundadores */}
      {(founderLabel || founder1Name || founder2Name) && (
        <div className="mb-16">
          {founderLabel && <h3 className="text-lg font-bold mb-6" style={{ color: "var(--site-on-surface)" }}>{founderLabel}</h3>}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {founder1Name && founder1Image && (
              <div className="flex gap-4 items-start">
                <div className="relative w-24 h-24 md:w-28 md:h-28 flex-shrink-0 rounded-full overflow-hidden">
                  <OptimizedImage src={founder1Image} alt={founder1Name} fill sizes="112px" className="object-cover" />
                </div>
                <div>
                  <h4 className="text-lg font-bold" style={{ color: "var(--site-on-surface)" }}>{founder1Name}</h4>
                  {founder1Role && <p className="text-sm" style={{ color: "var(--site-primary)" }}>{founder1Role}</p>}
                  {founderBio && <div className="prose prose-sm mt-2" style={{ color: "var(--site-on-surface-variant)" }} dangerouslySetInnerHTML={{ __html: founderBio }} />}
                </div>
              </div>
            )}
            {founder2Name && founder2Image && (
              <div className="flex gap-4 items-start">
                <div className="relative w-24 h-24 md:w-28 md:h-28 flex-shrink-0 rounded-full overflow-hidden">
                  <OptimizedImage src={founder2Image} alt={founder2Name} fill sizes="112px" className="object-cover" />
                </div>
                <div>
                  <h4 className="text-lg font-bold" style={{ color: "var(--site-on-surface)" }}>{founder2Name}</h4>
                  {founder2Role && <p className="text-sm" style={{ color: "var(--site-primary)" }}>{founder2Role}</p>}
                  {founderBio2 && <div className="prose prose-sm mt-2" style={{ color: "var(--site-on-surface-variant)" }} dangerouslySetInnerHTML={{ __html: founderBio2 }} />}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Valores */}
      {valores && valores.length > 0 && (
        <div className="mb-16">
          {valuesEyebrow && <span className="ccf-kicker inline-flex items-center gap-2 text-xs uppercase mb-4" style={{ color: "var(--site-primary)" }}>{valuesEyebrow}</span>}
          {valoresTitle && <h3 className="text-2xl font-bold mb-8" style={{ color: "var(--site-on-surface)" }}>{valoresTitle}</h3>}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {valores.map((valor, i) => (
              <div key={i} className="p-5 rounded-xl border" style={{ borderColor: "var(--site-outline)", background: "var(--site-surface-container)" }}>
                {valor.num && <span className="text-xs font-bold uppercase tracking-widest mb-2 inline-block" style={{ color: "var(--site-primary)" }}>{valor.num}</span>}
                {valor.title && <h4 className="font-bold mb-2" style={{ color: "var(--site-on-surface)" }}>{valor.title}</h4>}
                {valor.desc && <p className="text-sm leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>{valor.desc}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cita */}
      {quoteText && (
        <div className="mb-16 p-8 rounded-2xl text-center" style={{ background: "linear-gradient(135deg, var(--site-primary-container), var(--site-secondary-container, var(--site-primary-container)))" }}>
          <blockquote className="text-xl md:text-2xl italic font-medium max-w-3xl mx-auto" style={{ color: "var(--site-on-primary-container)" }}>
            &ldquo;{quoteText}&rdquo;
          </blockquote>
          {quoteAuthor && (
            <cite className="block mt-4 text-base font-normal" style={{ color: "var(--site-on-primary-container)" }}>
              {quoteAuthor}
              {quoteSubtitle && <span className="block text-sm opacity-80 mt-1">{quoteSubtitle}</span>}
            </cite>
          )}
        </div>
      )}

      {/* CTA Final */}
      {(ctaTitle || founderCtaTeam || founderCtaVisit || ctaViewSedes || ctaViewEvents) && (
        <div className="text-center">
          {ctaTitle && <h3 className="text-2xl md:text-3xl font-bold mb-3" style={{ color: "var(--site-on-surface)" }}>{ctaTitle}</h3>}
          {ctaDesc && <p className="max-w-xl mx-auto mb-6" style={{ color: "var(--site-on-surface-variant)" }}>{ctaDesc}</p>}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            {founderCtaTeam && (
              <Link href="/pastores" className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-lg transition-transform hover:scale-105" style={{ background: "var(--site-cta-gradient)" }}>
                {founderCtaTeam}
              </Link>
            )}
            {founderCtaVisit && (
              <Link href="/sedes" className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest transition-transform hover:scale-105" style={{ border: "2px solid var(--site-primary)", color: "var(--site-primary)" }}>
                {founderCtaVisit}
              </Link>
            )}
            {ctaViewSedes && (
              <Link href="/sedes" className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-bold uppercase tracking-widest transition-opacity hover:opacity-70" style={{ color: "var(--site-primary)" }}>
                {ctaViewSedes} →
              </Link>
            )}
            {ctaViewEvents && (
              <Link href="/eventos" className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-bold uppercase tracking-widest transition-opacity hover:opacity-70" style={{ color: "var(--site-primary)" }}>
                {ctaViewEvents} →
              </Link>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

export function CtaBannerSection({ section }: { section: CmsSection<"cta_banner"> }) {
  const props: CtaBannerProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const body = val(p, "body", "");
  const ctaLabel = val(p, "cta_label", "");
  const ctaHref = val(p, "cta_href", "/");
  const ctaLabel2 = val(p, "cta_label_2", "");
  const ctaHref2 = val(p, "cta_href_2", "/");

  return (
    <section
      className="ccf-section-panel p-8 md:p-14 lg:p-16 text-center"
      style={{ background: "linear-gradient(135deg, var(--site-primary-container), var(--site-secondary-container, var(--site-primary-container)))" }}
    >
      {title && (
        <h2 className="text-2xl md:text-4xl font-black tracking-tight max-w-2xl mx-auto" style={{ color: "var(--site-on-primary-container)" }}>
          {title}
        </h2>
      )}
      {body && (
        <p className="mt-4 text-base md:text-lg max-w-xl mx-auto leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
          {body}
        </p>
      )}
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        {ctaLabel && (
          <Link
            href={ctaHref}
            className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-lg transition-transform hover:scale-105"
            style={{ background: "var(--site-cta-gradient)" }}
          >
            {ctaLabel}
          </Link>
        )}
        {ctaLabel2 && (
          <Link
            href={ctaHref2}
            className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest transition-transform hover:scale-105"
            style={{ border: "2px solid var(--site-primary)", color: "var(--site-primary)" }}
          >
            {ctaLabel2}
          </Link>
        )}
      </div>
    </section>
  );
}

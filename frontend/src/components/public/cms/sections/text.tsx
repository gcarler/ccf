"use client";

import { CmsSection } from "@/types/cms-v2";
import type {
  RichTextProps,
  RichTextColumnsProps,
  CardsProps,
  CtaBannerProps,
} from "@/types/cms-section-props";
import Link from "next/link";
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

// ─── CTA Banner ────────────────────────────────────────────────────────────────

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

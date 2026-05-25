"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { CmsSection } from "@/types/cms-v2";
import { X, Star, ChevronDown, ChevronUp, Send, Calendar, MapPin, Upload, ChevronRight, Plus, Minus, FileText, CheckCircle2 } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

function val(props: Record<string, unknown>, key: string, fallback = "") {
  const value = props?.[key];
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function asItems(props: Record<string, unknown>): Array<Record<string, unknown>> {
  return Array.isArray(props.items)
    ? (props.items as Array<Record<string, unknown>>).filter(
        (item) => Boolean(item) && (item as { status?: string }).status !== "archived"
      )
    : [];
}

// ─── Hero ──────────────────────────────────────────────────────────────────────

function HeroSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Bienvenidos");
  const body = val(props, "body", "");
  const ctaLabel = val(props, "cta_label", "");
  const ctaHref = val(props, "cta_href", "/");
  const imageUrl = val(props, "image_url", "");
  const imageAlt = val(props, "image_alt", title);

  if (imageUrl) {
    return (
      <section className="relative overflow-hidden rounded-2xl min-h-[520px] flex items-end">
        <img src={imageUrl} alt={imageAlt} className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.82) 0%, rgba(0,0,0,0.3) 55%, transparent 100%)" }} />
        <div className="relative z-10 w-full p-6 md:p-10 lg:p-14">
          <h1 className="text-3xl md:text-5xl lg:text-6xl font-black tracking-tight text-white leading-tight max-w-3xl">
            {title}
          </h1>
          {body && (
            <p className="mt-4 text-base md:text-xl text-white/85 max-w-2xl leading-relaxed">
              {body}
            </p>
          )}
          {ctaLabel && (
            <Link
              href={ctaHref}
              className="inline-flex mt-6 items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-lg transition-transform hover:scale-105"
              style={{ background: "var(--faro-primary)" }}
            >
              {ctaLabel}
            </Link>
          )}
        </div>
      </section>
    );
  }

  return (
    <section
      className="rounded-2xl p-8 md:p-12 lg:p-16 min-h-[380px] flex items-center"
      style={{ background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))" }}
    >
      <div className="max-w-3xl">
        <h1 className="text-3xl md:text-5xl lg:text-6xl font-black tracking-tight text-white leading-tight">
          {title}
        </h1>
        {body && (
          <p className="mt-5 text-base md:text-xl text-white/85 max-w-2xl leading-relaxed">
            {body}
          </p>
        )}
        {ctaLabel && (
          <Link
            href={ctaHref}
            className="inline-flex mt-8 items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest bg-white shadow-lg transition-transform hover:scale-105"
            style={{ color: "var(--faro-primary)" }}
          >
            {ctaLabel}
          </Link>
        )}
      </div>
    </section>
  );
}

// ─── Video Hero ────────────────────────────────────────────────────────────────

function VideoHeroSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const body = val(props, "body", "");
  const ctaLabel = val(props, "cta_label", "");
  const ctaHref = val(props, "cta_href", "/");
  const videoUrl = val(props, "video_url", "");

  return (
    <section className="relative overflow-hidden rounded-2xl min-h-[480px] flex items-center">
      {videoUrl && (
        <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover">
          <source src={videoUrl} type="video/mp4" />
        </video>
      )}
      <div className="absolute inset-0" style={{ background: "linear-gradient(to right, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.3) 100%)" }} />
      <div className="relative z-10 p-8 md:p-12 lg:p-16 max-w-3xl">
        <h1 className="text-3xl md:text-5xl font-black tracking-tight text-white leading-tight">
          {title}
        </h1>
        {body && <p className="mt-5 text-base md:text-xl text-white/85 max-w-xl leading-relaxed">{body}</p>}
        {ctaLabel && (
          <Link
            href={ctaHref}
            className="inline-flex mt-8 items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-lg transition-transform hover:scale-105"
            style={{ background: "var(--faro-primary)" }}
          >
            {ctaLabel}
          </Link>
        )}
      </div>
    </section>
  );
}

// ─── Rich Text ─────────────────────────────────────────────────────────────────

function RichTextSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const body = val(props, "body", "");
  const ctaLabel = val(props, "cta_label", "");
  const ctaHref = val(props, "cta_href", "");

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--faro-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-4" style={{ color: "var(--faro-on-surface)" }}>
          {title}
        </h2>
      )}
      {body && (
        <div className="prose prose-base max-w-3xl leading-relaxed whitespace-pre-line" style={{ color: "var(--faro-on-surface-variant)" }}>
          {body}
        </div>
      )}
      {ctaLabel && ctaHref && (
        <Link
          href={ctaHref}
          className="inline-flex mt-6 items-center gap-2 text-sm font-bold uppercase tracking-widest transition-opacity hover:opacity-70"
          style={{ color: "var(--faro-primary)" }}
        >
          {ctaLabel} →
        </Link>
      )}
    </section>
  );
}

// ─── Rich Text Columns ─────────────────────────────────────────────────────────

function RichTextColumnsSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const body = val(props, "body", "");
  const body2 = val(props, "body_2", body);

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--faro-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-6" style={{ color: "var(--faro-on-surface)" }}>
          {title}
        </h2>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-10">
        <div className="leading-relaxed whitespace-pre-line text-base" style={{ color: "var(--faro-on-surface-variant)" }}>
          {body}
        </div>
        <div className="leading-relaxed whitespace-pre-line text-base" style={{ color: "var(--faro-on-surface-variant)" }}>
          {body2}
        </div>
      </div>
    </section>
  );
}

// ─── Cards ─────────────────────────────────────────────────────────────────────

function CardsSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const body = val(props, "body", "");
  const items = asItems(props).slice(0, 9) as Array<{ title?: string; body?: string; href?: string; icon?: string }>;

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--faro-surface-container-low)" }}>
      {(title || body) && (
        <div className="mb-8">
          {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--faro-on-surface)" }}>{title}</h2>}
          {body && <p className="mt-3 text-base max-w-2xl" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((card, i) => {
          const inner = (
            <>
              {card.icon && <span className="text-3xl">{card.icon}</span>}
              <h3 className="text-lg font-bold" style={{ color: "var(--faro-on-surface)" }}>{card.title || `Tarjeta ${i + 1}`}</h3>
              {card.body && <p className="text-sm leading-relaxed flex-1" style={{ color: "var(--faro-on-surface-variant)" }}>{card.body}</p>}
              {card.href && (
                <span className="text-xs font-bold uppercase tracking-widest mt-1" style={{ color: "var(--faro-primary)" }}>
                  Ver más →
                </span>
              )}
            </>
          );
          const cls = `rounded-xl p-6 flex flex-col gap-3 ${card.href ? "transition-transform hover:-translate-y-1 hover:shadow-md" : ""}`;
          const sty = { background: "var(--faro-surface-container)" };
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

function CtaBannerSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const body = val(props, "body", "");
  const ctaLabel = val(props, "cta_label", "");
  const ctaHref = val(props, "cta_href", "/");
  const ctaLabel2 = val(props, "cta_label_2", "");
  const ctaHref2 = val(props, "cta_href_2", "/");

  return (
    <section
      className="rounded-2xl p-8 md:p-12 text-center"
      style={{ background: "linear-gradient(135deg, var(--faro-primary-container), var(--faro-secondary-container, var(--faro-primary-container)))" }}
    >
      {title && (
        <h2 className="text-2xl md:text-4xl font-black tracking-tight max-w-2xl mx-auto" style={{ color: "var(--faro-on-primary-container)" }}>
          {title}
        </h2>
      )}
      {body && (
        <p className="mt-4 text-base md:text-lg max-w-xl mx-auto leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>
          {body}
        </p>
      )}
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        {ctaLabel && (
          <Link
            href={ctaHref}
            className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-lg transition-transform hover:scale-105"
            style={{ background: "var(--faro-primary)" }}
          >
            {ctaLabel}
          </Link>
        )}
        {ctaLabel2 && (
          <Link
            href={ctaHref2}
            className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest transition-transform hover:scale-105"
            style={{ border: "2px solid var(--faro-primary)", color: "var(--faro-primary)" }}
          >
            {ctaLabel2}
          </Link>
        )}
      </div>
    </section>
  );
}

// ─── Gallery ───────────────────────────────────────────────────────────────────

function GallerySection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const body = val(props, "body", "");
  const imageUrl = val(props, "image_url", "");
  const imageAlt = val(props, "image_alt", title || "Imagen");
  const items = asItems(props) as Array<{ url?: string; alt?: string; caption?: string }>;

  const images = items.length > 0
    ? items.map((item) => ({ url: item.url || "", alt: item.alt || "", caption: item.caption || "" }))
    : imageUrl
    ? [{ url: imageUrl, alt: imageAlt, caption: "" }]
    : [];

  if (images.length === 0) return null;

  const isGrid = images.length > 1;

  return (
    <section className="rounded-2xl overflow-hidden" style={{ background: "var(--faro-surface-container-low)" }}>
      {isGrid ? (
        <div className={`grid gap-1 ${images.length === 2 ? "grid-cols-2" : images.length === 3 ? "grid-cols-3" : "grid-cols-2 md:grid-cols-4"}`}>
          {images.map((img, i) => (
            <div key={i} className="relative aspect-square group overflow-hidden">
              <img src={img.url} alt={img.alt} className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" />
              {img.caption && (
                <div className="absolute inset-x-0 bottom-0 p-3 opacity-0 group-hover:opacity-100 transition-opacity" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.7), transparent)" }}>
                  <p className="text-xs text-white font-medium">{img.caption}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <img src={images[0].url} alt={images[0].alt} className="w-full max-h-[480px] object-cover" />
      )}
      {(title || body) && (
        <div className="p-6">
          {title && <h3 className="text-xl font-bold" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>}
          {body && <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
        </div>
      )}
    </section>
  );
}

// ─── FAQ ───────────────────────────────────────────────────────────────────────

function FaqSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const items = asItems(props).slice(0, 12) as Array<{ q?: string; a?: string }>;
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--faro-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-6" style={{ color: "var(--faro-on-surface)" }}>{title}</h2>}
      <div className="space-y-2">
        {items.map((item, i) => {
          const isOpen = openIndex === i;
          return (
            <div key={i} className="rounded-xl overflow-hidden" style={{ background: "var(--faro-surface-container)" }}>
              <button
                onClick={() => setOpenIndex(isOpen ? null : i)}
                className="w-full flex items-center justify-between gap-4 p-5 text-left"
              >
                <span className="font-bold text-base" style={{ color: "var(--faro-on-surface)" }}>
                  {item.q || `Pregunta ${i + 1}`}
                </span>
                {isOpen ? (
                  <ChevronUp size={18} style={{ color: "var(--faro-primary)", flexShrink: 0 }} />
                ) : (
                  <ChevronDown size={18} style={{ color: "var(--faro-on-surface-variant)", flexShrink: 0 }} />
                )}
              </button>
              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <p className="px-5 pb-5 text-sm leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>
                      {item.a || "Respuesta pendiente"}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ─── Embed ─────────────────────────────────────────────────────────────────────

function EmbedSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const body = val(props, "body", "");
  const embedUrl = val(props, "embed_url", "");

  return (
    <section className="rounded-2xl p-6" style={{ background: "var(--faro-surface-container-low)" }}>
      {title && <h3 className="text-xl font-bold mb-3" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>}
      {body && <p className="mb-4 text-sm leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
      {embedUrl ? (
        <div className="aspect-video rounded-xl overflow-hidden" style={{ background: "var(--faro-surface-container)" }}>
          <iframe title={title} src={embedUrl} className="w-full h-full border-0" allowFullScreen />
        </div>
      ) : (
        <div className="aspect-video rounded-xl flex items-center justify-center text-sm" style={{ background: "var(--faro-surface-container)", color: "var(--faro-on-surface-variant)" }}>
          Sin URL de embed configurada
        </div>
      )}
    </section>
  );
}

// ─── Testimonials ──────────────────────────────────────────────────────────────

function TestimonialsSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Testimonios");
  const items = asItems(props).slice(0, 6) as Array<{ author?: string; role?: string; content?: string; stars?: number | string }>;

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--faro-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight text-center mb-8" style={{ color: "var(--faro-on-surface)" }}>
          {title}
        </h2>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((item, i) => {
          const stars = typeof item.stars === "number" ? item.stars : typeof item.stars === "string" ? parseInt(item.stars, 10) : 5;
          return (
            <article key={i} className="rounded-xl p-6 flex flex-col gap-4" style={{ background: "var(--faro-surface-container)" }}>
              <div className="flex gap-0.5">
                {Array.from({ length: 5 }).map((_, si) => (
                  <Star key={si} size={14} fill={si < stars ? "var(--faro-primary)" : "none"} stroke={si < stars ? "var(--faro-primary)" : "var(--faro-on-surface-variant)"} />
                ))}
              </div>
              <p className="text-base leading-relaxed italic flex-1" style={{ color: "var(--faro-on-surface)" }}>
                &ldquo;{item.content || "Testimonio"}&rdquo;
              </p>
              <div className="flex items-center gap-3 pt-2 border-t" style={{ borderColor: "var(--faro-outline-variant, rgba(0,0,0,0.1))" }}>
                <div
                  className="size-10 rounded-full flex items-center justify-center font-black text-white text-sm flex-shrink-0"
                  style={{ background: "var(--faro-primary)" }}
                >
                  {(item.author || "A")[0].toUpperCase()}
                </div>
                <div>
                  <p className="font-bold text-sm" style={{ color: "var(--faro-on-surface)" }}>{item.author || "Anónimo"}</p>
                  {item.role && <p className="text-xs" style={{ color: "var(--faro-on-surface-variant)" }}>{item.role}</p>}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

// ─── Stats ─────────────────────────────────────────────────────────────────────

function AnimatedNumber({ target }: { target: string }) {
  const [display, setDisplay] = useState("0");
  const ref = useRef<HTMLSpanElement>(null);
  const hasAnimated = useRef(false);

  const extractNumber = (str: string) => {
    const match = str.match(/[\d,]+/);
    return match ? parseInt(match[0].replace(/,/g, ""), 10) : null;
  };

  const startAnimation = useCallback(() => {
    if (hasAnimated.current) return;
    const num = extractNumber(target);
    if (!num || num > 1_000_000) {
      setDisplay(target);
      hasAnimated.current = true;
      return;
    }
    hasAnimated.current = true;
    const suffix = target.replace(/[\d,]/g, "");
    const duration = 1500;
    const steps = 40;
    let step = 0;
    const timer = setInterval(() => {
      step++;
      const progress = step / steps;
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(eased * num);
      setDisplay(`${current.toLocaleString()}${suffix}`);
      if (step >= steps) {
        clearInterval(timer);
        setDisplay(target);
      }
    }, duration / steps);
  }, [target]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) startAnimation(); },
      { threshold: 0.5 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [startAnimation]);

  return <span ref={ref}>{display}</span>;
}

function StatsSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const items = asItems(props).slice(0, 6) as Array<{ value?: string; label?: string }>;

  return (
    <section
      className="rounded-2xl p-8 md:p-12"
      style={{ background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary, var(--faro-primary)))" }}
    >
      {title && (
        <h2 className="text-xl md:text-2xl font-black tracking-tight text-center text-white mb-8">{title}</h2>
      )}
      <div className={`grid gap-6 text-center ${items.length <= 2 ? "grid-cols-2" : items.length === 3 ? "grid-cols-3" : "grid-cols-2 md:grid-cols-4"}`}>
        {items.map((item, i) => (
          <div key={i}>
            <p className="text-3xl md:text-4xl font-black text-white">
              <AnimatedNumber target={item.value || "0"} />
            </p>
            <p className="mt-2 text-xs font-bold uppercase tracking-widest text-white/70">{item.label || "Métrica"}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Team ──────────────────────────────────────────────────────────────────────

function TeamSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Nuestro Equipo");
  const items = asItems(props).slice(0, 12) as Array<{ name?: string; role?: string; image?: string; bio?: string }>;

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--faro-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight text-center mb-8" style={{ color: "var(--faro-on-surface)" }}>
          {title}
        </h2>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-6 text-center">
        {items.map((item, i) => (
          <div key={i} className="flex flex-col items-center gap-3">
            <div
              className="size-20 md:size-24 rounded-full overflow-hidden flex items-center justify-center font-black text-white text-2xl flex-shrink-0"
              style={{
                background: item.image ? undefined : "var(--faro-primary)",
                backgroundImage: item.image ? `url('${item.image}')` : undefined,
                backgroundSize: "cover",
                backgroundPosition: "center",
              }}
            >
              {!item.image && (item.name || "?")[0].toUpperCase()}
            </div>
            <div>
              <p className="font-bold text-base" style={{ color: "var(--faro-on-surface)" }}>{item.name || "Nombre"}</p>
              {item.role && <p className="text-xs font-medium mt-0.5" style={{ color: "var(--faro-primary)" }}>{item.role}</p>}
              {item.bio && <p className="text-xs mt-2 leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>{item.bio}</p>}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Countdown ─────────────────────────────────────────────────────────────────

function CountdownSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Próximo Evento");
  const targetDate = val(props, "target_date", "");
  const body = val(props, "body", "");

  const [timeLeft, setTimeLeft] = useState({ d: 0, h: 0, m: 0, s: 0, expired: false });

  useEffect(() => {
    if (!targetDate) return;
    const target = new Date(targetDate).getTime();

    const tick = () => {
      const now = Date.now();
      const diff = target - now;
      if (diff <= 0) {
        setTimeLeft({ d: 0, h: 0, m: 0, s: 0, expired: true });
        return;
      }
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setTimeLeft({ d, h, m, s, expired: false });
    };

    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [targetDate]);

  const units = [
    { label: "DÍAS", value: timeLeft.d },
    { label: "HORAS", value: timeLeft.h },
    { label: "MIN", value: timeLeft.m },
    { label: "SEG", value: timeLeft.s },
  ];

  return (
    <section
      className="rounded-2xl p-8 md:p-12 text-center"
      style={{ background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary, var(--faro-primary)))" }}
    >
      <h2 className="text-2xl md:text-3xl font-black text-white">{title}</h2>
      {body && <p className="mt-3 text-white/80 text-base">{body}</p>}
      {timeLeft.expired ? (
        <p className="mt-8 text-white text-xl font-bold">¡El evento ya comenzó!</p>
      ) : (
        <div className="mt-8 flex justify-center gap-3 md:gap-6">
          {units.map((unit) => (
            <div key={unit.label} className="flex flex-col items-center gap-2">
              <div
                className="size-16 md:size-20 rounded-xl flex items-center justify-center text-2xl md:text-3xl font-black text-white"
                style={{ background: "rgba(255,255,255,0.15)", backdropFilter: "blur(8px)" }}
              >
                {String(unit.value).padStart(2, "0")}
              </div>
              <span className="text-[10px] font-bold uppercase tracking-widest text-white/70">{unit.label}</span>
            </div>
          ))}
        </div>
      )}
      {targetDate && !timeLeft.expired && (
        <p className="mt-6 text-white/60 text-xs">
          {new Date(targetDate).toLocaleDateString("es", { weekday: "long", year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" })}
        </p>
      )}
    </section>
  );
}

// ─── Pricing ───────────────────────────────────────────────────────────────────

function PricingSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Opciones");
  const items = asItems(props).slice(0, 4) as Array<{ name?: string; price?: string; features?: string; btn?: string; btn_href?: string; featured?: boolean | string }>;

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--faro-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight text-center mb-8" style={{ color: "var(--faro-on-surface)" }}>
          {title}
        </h2>
      )}
      <div className={`grid grid-cols-1 gap-4 ${items.length >= 3 ? "md:grid-cols-3" : "md:grid-cols-2 max-w-2xl mx-auto"}`}>
        {items.map((item, i) => {
          const featured = item.featured === true || item.featured === "true" || item.featured === "1";
          return (
            <article
              key={i}
              className={`rounded-xl p-6 flex flex-col gap-4 relative ${featured ? "shadow-xl scale-[1.02]" : ""}`}
              style={{
                background: featured ? "var(--faro-primary)" : "var(--faro-surface-container)",
                border: featured ? "none" : "1px solid transparent",
              }}
            >
              {featured && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full px-4 py-1 text-[10px] font-black uppercase tracking-widest bg-white" style={{ color: "var(--faro-primary)" }}>
                  Recomendado
                </span>
              )}
              <div>
                <h3 className="text-lg font-black" style={{ color: featured ? "white" : "var(--faro-on-surface)" }}>
                  {item.name || `Plan ${i + 1}`}
                </h3>
                <p className="text-3xl font-black mt-1" style={{ color: featured ? "white" : "var(--faro-primary)" }}>
                  {item.price || "—"}
                </p>
              </div>
              <ul className="space-y-2 flex-1">
                {(item.features || "").split("\n").filter(Boolean).map((feat, fi) => (
                  <li key={fi} className="flex items-start gap-2 text-sm" style={{ color: featured ? "rgba(255,255,255,0.85)" : "var(--faro-on-surface-variant)" }}>
                    <span className="mt-0.5 flex-shrink-0 font-black" style={{ color: featured ? "white" : "var(--faro-primary)" }}>✓</span>
                    {feat}
                  </li>
                ))}
              </ul>
              {item.btn && (
                item.btn_href ? (
                  <Link
                    href={item.btn_href}
                    className="w-full py-3 rounded-full text-sm font-black uppercase tracking-widest text-center block transition-opacity hover:opacity-90"
                    style={{ background: featured ? "white" : "var(--faro-primary)", color: featured ? "var(--faro-primary)" : "white" }}
                  >
                    {item.btn}
                  </Link>
                ) : (
                  <button
                    className="w-full py-3 rounded-full text-sm font-black uppercase tracking-widest transition-opacity hover:opacity-90"
                    style={{ background: featured ? "white" : "var(--faro-primary)", color: featured ? "var(--faro-primary)" : "white" }}
                  >
                    {item.btn}
                  </button>
                )
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

// ─── Image + Text ──────────────────────────────────────────────────────────────

function ImageTextSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const body = val(props, "body", "");
  const imageUrl = val(props, "image_url", "");
  const imageAlt = val(props, "image_alt", title);
  const ctaLabel = val(props, "cta_label", "");
  const ctaHref = val(props, "cta_href", "/");
  const side = val(props, "image_side", "right"); // "left" | "right"

  const textCol = (
    <div className="flex flex-col justify-center gap-5 py-4 md:py-0">
      {title && <h2 className="text-2xl md:text-4xl font-black tracking-tight leading-tight" style={{ color: "var(--faro-on-surface)" }}>{title}</h2>}
      {body && <p className="text-base leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
      {ctaLabel && (
        <Link
          href={ctaHref}
          className="inline-flex self-start items-center gap-2 rounded-full px-5 py-2.5 text-sm font-bold uppercase tracking-widest text-white transition-transform hover:scale-105"
          style={{ background: "var(--faro-primary)" }}
        >
          {ctaLabel}
        </Link>
      )}
    </div>
  );

  const imgCol = imageUrl ? (
    <div className="relative rounded-xl overflow-hidden aspect-[4/3]">
      <img src={imageUrl} alt={imageAlt} className="w-full h-full object-cover" />
    </div>
  ) : null;

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--faro-surface-container-low)" }}>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12 items-center">
        {side === "left" && imgCol}
        {textCol}
        {side !== "left" && imgCol}
      </div>
    </section>
  );
}

// ─── Timeline ──────────────────────────────────────────────────────────────────

function TimelineSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const items = asItems(props) as Array<{ year?: string; title?: string; body?: string }>;

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--faro-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-8" style={{ color: "var(--faro-on-surface)" }}>{title}</h2>}
      <div className="relative">
        <div className="absolute left-6 top-0 bottom-0 w-0.5" style={{ background: "var(--faro-primary)", opacity: 0.3 }} />
        <div className="space-y-6">
          {items.map((item, i) => (
            <div key={i} className="relative pl-16">
              <div
                className="absolute left-0 size-12 rounded-full flex items-center justify-center text-xs font-black text-white leading-tight text-center"
                style={{ background: "var(--faro-primary)" }}
              >
                {item.year || String(i + 1)}
              </div>
              <div className="rounded-xl p-5" style={{ background: "var(--faro-surface-container)" }}>
                {item.title && <h3 className="font-black text-base" style={{ color: "var(--faro-on-surface)" }}>{item.title}</h3>}
                {item.body && <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>{item.body}</p>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Icon Grid ─────────────────────────────────────────────────────────────────

function IconGridSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const body = val(props, "body", "");
  const items = asItems(props).slice(0, 12) as Array<{ icon?: string; title?: string; body?: string }>;

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--faro-surface-container-low)" }}>
      {(title || body) && (
        <div className="mb-8 text-center">
          {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--faro-on-surface)" }}>{title}</h2>}
          {body && <p className="mt-3 text-base max-w-2xl mx-auto" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
        </div>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
        {items.map((item, i) => (
          <div key={i} className="rounded-xl p-5 flex flex-col items-center text-center gap-3" style={{ background: "var(--faro-surface-container)" }}>
            {item.icon && <span className="text-4xl">{item.icon}</span>}
            <h3 className="font-black text-sm" style={{ color: "var(--faro-on-surface)" }}>{item.title || `Item ${i + 1}`}</h3>
            {item.body && <p className="text-xs leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>{item.body}</p>}
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Newsletter ────────────────────────────────────────────────────────────────

function NewsletterSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Mantente conectado");
  const body = val(props, "body", "");
  const btnLabel = val(props, "cta_label", "Suscribirse");
  const actionUrl = val(props, "action_url", "");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes("@")) return;
    setLoading(true);
    try {
      if (actionUrl) {
        await fetch(actionUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email }),
        });
      }
      setSent(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      className="rounded-2xl p-8 md:p-12 text-center"
      style={{ background: "linear-gradient(135deg, var(--faro-primary-container), var(--faro-surface-container))" }}
    >
      <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--faro-on-surface)" }}>{title}</h2>
      {body && <p className="mt-3 text-base max-w-xl mx-auto" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
      {sent ? (
        <div className="mt-8 inline-flex items-center gap-3 rounded-xl px-6 py-4" style={{ background: "var(--faro-surface-container)" }}>
          <span className="text-2xl">🎉</span>
          <p className="font-bold" style={{ color: "var(--faro-on-surface)" }}>¡Gracias! Te mantendremos al tanto.</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-8 flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Tu nombre"
            className="flex-1 rounded-xl px-4 py-3 text-sm border outline-none"
            style={{ background: "var(--faro-surface-container)", borderColor: "var(--faro-outline-variant, rgba(0,0,0,0.15))", color: "var(--faro-on-surface)" }}
          />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="tu@email.com"
            required
            className="flex-1 rounded-xl px-4 py-3 text-sm border outline-none"
            style={{ background: "var(--faro-surface-container)", borderColor: "var(--faro-outline-variant, rgba(0,0,0,0.15))", color: "var(--faro-on-surface)" }}
          />
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-bold text-white whitespace-nowrap disabled:opacity-60 transition-opacity hover:opacity-90"
            style={{ background: "var(--faro-primary)" }}
          >
            <Send size={14} /> {loading ? "Enviando..." : btnLabel}
          </button>
        </form>
      )}
    </section>
  );
}

// ─── Popup Banner ──────────────────────────────────────────────────────────────

function PopupBlock({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Aviso Importante");
  const body = val(props, "body", "");
  const ctaLabel = val(props, "cta_label", "Ver Más");
  const ctaHref = val(props, "cta_href", "/");
  const delayMs = parseInt(val(props, "delay_ms", "2000"), 10) || 2000;

  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const popupId = `faro_popup_${section.id}`;
    if (!sessionStorage.getItem(popupId)) {
      const timer = setTimeout(() => setIsVisible(true), delayMs);
      return () => clearTimeout(timer);
    }
  }, [section.id, delayMs]);

  const handleClose = () => {
    setIsVisible(false);
    sessionStorage.setItem(`faro_popup_${section.id}`, "closed");
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="absolute inset-0 backdrop-blur-sm"
            style={{ background: "rgba(0,0,0,0.5)" }}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: 24 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 24 }}
            className="relative w-full max-w-md rounded-2xl p-8 shadow-2xl"
            style={{ background: "var(--faro-surface-container)" }}
          >
            <button
              onClick={handleClose}
              className="absolute top-4 right-4 p-2 rounded-full transition-colors"
              style={{ background: "var(--faro-surface-container-high, rgba(0,0,0,0.05))" }}
            >
              <X size={18} style={{ color: "var(--faro-on-surface-variant)" }} />
            </button>
            <div className="text-center mt-2">
              <h2 className="text-xl font-black mb-3" style={{ color: "var(--faro-on-surface)" }}>{title}</h2>
              <p className="text-sm leading-relaxed mb-6" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>
              <div className="flex flex-col gap-3">
                <Link
                  href={ctaHref}
                  onClick={handleClose}
                  className="w-full py-3 rounded-full text-sm font-black uppercase tracking-widest text-white text-center transition-transform hover:scale-[1.02]"
                  style={{ background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary, var(--faro-primary)))" }}
                >
                  {ctaLabel}
                </Link>
                <button
                  onClick={handleClose}
                  className="w-full py-3 rounded-full text-sm font-bold transition-opacity hover:opacity-70"
                  style={{ color: "var(--faro-on-surface-variant)" }}
                >
                  No, gracias
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

// ─── Button Row ────────────────────────────────────────────────────────────────

function ButtonSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const buttons = (Array.isArray(props.buttons) ? props.buttons : [{ label: "Click", href: "/" }]) as Array<{ label: string; href: string; variant?: string; size?: string; icon?: string }>;
  const align = val(props, "align", "center");
  const gap = val(props, "gap", "4");

  const sizeClasses: Record<string, string> = { sm: "text-xs px-3 py-1.5", md: "text-sm px-4 py-2", lg: "text-base px-6 py-3" };
  const variantBg: Record<string, string> = { primary: "var(--faro-primary)", outline: "transparent", ghost: "transparent" };
  const variantBorder: Record<string, string> = { primary: "var(--faro-primary)", outline: "var(--faro-outline-variant)", ghost: "transparent" };
  const variantColor: Record<string, string> = { primary: "var(--faro-on-primary)", outline: "var(--faro-on-surface)", ghost: "var(--faro-primary)" };

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className={`flex flex-wrap gap-${gap} ${align === "center" ? "justify-center" : align === "right" ? "justify-end" : "justify-start"}`}>
        {buttons.map((btn, i) => (
          <Link
            key={i}
            href={btn.href || "#"}
            className={`rounded-lg font-semibold transition-all hover:scale-105 ${sizeClasses[btn.size || "md"]}`}
            style={{
              background: variantBg[btn.variant || "primary"],
              border: `2px solid ${variantBorder[btn.variant || "primary"]}`,
              color: variantColor[btn.variant || "primary"],
            }}
          >
            {btn.label}
            {btn.icon && <ChevronRight size={16} className="inline ml-1" />}
          </Link>
        ))}
      </div>
    </section>
  );
}

// ─── TOC ───────────────────────────────────────────────────────────────────────

function TocSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "En esta página");
  const items = asItems(props).filter(Boolean);
  return (
    <section className="py-6 md:py-8 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className="max-w-2xl rounded-lg p-4 border" style={{ background: "var(--faro-surface-container)", borderColor: "var(--faro-outline-variant)" }}>
        <h3 className="text-sm font-bold uppercase tracking-wide mb-3" style={{ color: "var(--faro-primary)" }}>{title}</h3>
        <nav>
          <ol className="space-y-2">
            {items.map((item, i) => (
              <li key={i}>
                <a href={val(item, "href", "#")} className="flex items-center gap-2 text-sm font-medium hover:underline" style={{ color: "var(--faro-on-surface)" }}>
                  <span className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold" style={{ background: "var(--faro-primary-container)", color: "var(--faro-primary)" }}>{i + 1}</span>
                  {val(item, "label", `Sección ${i + 1}`)}
                </a>
              </li>
            ))}
          </ol>
        </nav>
      </div>
    </section>
  );
}

// ─── Divider ───────────────────────────────────────────────────────────────────

function DividerSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const style = val(props, "style", "solid");
  const marginY = val(props, "margin_top", "8");
  const width = val(props, "width", "full");

  const styleClass = style === "dashed" ? "border-dashed" : style === "dotted" ? "border-dotted" : "border-solid";
  const widthClass = width === "full" ? "w-full" : width === "narrow" ? "w-1/3" : "w-2/3";

  return (
    <section className={`py-${marginY} px-3 md:px-6 lg:px-8 xl:px-12`}>
      <hr className={`${styleClass} border-t-2 mx-auto ${widthClass}`} style={{ borderColor: "var(--faro-outline-variant)" }} />
    </section>
  );
}

// ─── Collapsible ───────────────────────────────────────────────────────────────

function CollapsibleSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Información");
  const defaultOpen = props.default_open === true;
  const contentHtml = val(props, "content_html", "");
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="py-4 md:py-6 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className="rounded-lg border" style={{ background: "var(--faro-surface-container)", borderColor: "var(--faro-outline-variant)" }}>
        <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between p-4 text-left" style={{ color: "var(--faro-on-surface)" }}>
          <span className="font-bold text-lg">{title}</span>
          <ChevronDown size={20} className={`transition-transform duration-300 ${open ? "rotate-180" : ""}`} />
        </button>
        <AnimatePresence>
          {open && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
              <div className="px-4 pb-4" style={{ color: "var(--faro-on-surface-variant)" }} dangerouslySetInnerHTML={{ __html: contentHtml }} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}

// ─── Social Links ──────────────────────────────────────────────────────────────

function SocialLinksSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Síguenos");
  const links = asItems(props).filter(Boolean);
  const layout = val(props, "layout", "row");
  const showLabels = props.show_labels !== false;
  const iconSize = parseInt(val(props, "icon_size", "24"));

  const platformIcons: Record<string, React.ReactNode> = {
    facebook: <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="currentColor"><path d="M18 2h-3a5 5 0 00-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 011-1h3z" /></svg>,
    instagram: <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="2" width="20" height="20" rx="5" /><circle cx="12" cy="12" r="5" /><circle cx="17.5" cy="6.5" r="1.5" fill="currentColor" /></svg>,
    youtube: <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="currentColor"><path d="M22.54 6.42a2.78 2.78 0 00-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 00-1.94 2A29 29 0 001 11.75a29 29 0 00.46 5.33A2.78 2.78 0 003.4 19.1c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 001.94-2 29 29 0 00.46-5.25 29 29 0 00-.46-5.43z" /><polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02" fill="white" /></svg>,
    tiktok: <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="currentColor"><path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1v-3.5a6.37 6.37 0 00-.79-.05A6.34 6.34 0 003.15 15.2a6.34 6.34 0 0010.86 4.46V13a8.28 8.28 0 005.58 2.15V11.7a4.83 4.83 0 01-3.77-1.78V6.69h3.77z" /></svg>,
    whatsapp: <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z" /><path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.168L2 22l4.832-1.438A9.955 9.955 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2z" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg>,
    twitter: <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" /></svg>,
  };

  const containerClass = layout === "row" ? "flex flex-wrap gap-4" : layout === "grid" ? "grid grid-cols-2 md:grid-cols-4 gap-4" : "space-y-3";

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <h3 className="text-lg font-bold mb-4" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
      <div className={containerClass}>
        {links.map((link, i) => {
          const platform = val(link, "platform", "").toLowerCase();
          const url = val(link, "url", "#");
          const label = val(link, "label", platform);
          return (
            <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 p-3 rounded-lg border transition-all hover:scale-105" style={{ background: "var(--faro-surface)", borderColor: "var(--faro-outline-variant)", color: "var(--faro-on-surface)" }}>
              <span style={{ color: "var(--faro-primary)" }}>{platformIcons[platform] || <Star size={iconSize} />}</span>
              {showLabels && <span className="text-sm font-medium">{label}</span>}
            </a>
          );
        })}
      </div>
    </section>
  );
}

// ─── Spacer ────────────────────────────────────────────────────────────────────

function SpacerSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const height = parseInt(val(props, "height", "32"));
  return <div style={{ height: `${height}px` }} />;
}

// ─── Calendar ──────────────────────────────────────────────────────────────────

function CalendarSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Próximos Eventos");
  const items = asItems(props).filter(Boolean);
  const showTime = props.show_time !== false;
  const showLocation = props.show_location !== false;

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <h3 className="text-lg font-bold mb-6" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
      <div className="space-y-3">
        {items.length === 0 && <p className="text-sm opacity-60" style={{ color: "var(--faro-on-surface-variant)" }}>No hay eventos configurados.</p>}
        {items.map((item, i) => (
          <div key={i} className="flex items-start gap-4 p-4 rounded-lg border" style={{ background: "var(--faro-surface)", borderColor: "var(--faro-outline-variant)" }}>
            <div className="w-12 h-12 rounded-lg flex flex-col items-center justify-center shrink-0" style={{ background: "var(--faro-primary-container)", color: "var(--faro-primary)" }}>
              <Calendar size={18} />
            </div>
            <div className="flex-1">
              <p className="font-bold" style={{ color: "var(--faro-on-surface)" }}>{val(item, "title", "Evento")}</p>
              <div className="flex flex-wrap gap-3 text-xs mt-1" style={{ color: "var(--faro-on-surface-variant)" }}>
                {showTime && val(item, "date") && <span>{val(item, "date")}{showTime && val(item, "time") ? ` · ${val(item, "time")}` : ""}</span>}
                {showLocation && val(item, "location") && <span>{val(item, "location")}</span>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Map ───────────────────────────────────────────────────────────────────────

function MapSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Encuéntranos");
  const embedUrl = val(props, "embed_url", "");
  const address = val(props, "address", "");
  const height = parseInt(val(props, "height", "400"));
  const showDirections = props.show_directions_link !== false;

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <h3 className="text-lg font-bold mb-4" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
      {embedUrl ? (
        <div className="rounded-lg overflow-hidden border" style={{ borderColor: "var(--faro-outline-variant)" }}>
          <iframe src={embedUrl} width="100%" height={height} style={{ border: 0 }} allowFullScreen loading="lazy" />
        </div>
      ) : (
        <div className="rounded-lg border p-8 text-center" style={{ background: "var(--faro-surface-container)", borderColor: "var(--faro-outline-variant)", height: `${height}px` }}>
          <MapPin size={48} className="mx-auto mb-3 opacity-30" style={{ color: "var(--faro-primary)" }} />
          <p className="text-lg font-medium mb-2" style={{ color: "var(--faro-on-surface)" }}>{address || "Sin dirección configurada"}</p>
          {showDirections && address && (
            <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold" style={{ background: "var(--faro-primary)", color: "var(--faro-on-primary)" }}>
              <MapPin size={16} /> Ver en Google Maps
            </a>
          )}
        </div>
      )}
    </section>
  );
}

// ─── Document Upload ───────────────────────────────────────────────────────────

function DocumentUploadSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Subir Documento");
  const description = val(props, "description", "");
  const acceptedTypes = val(props, "accepted_types", ".pdf,.doc,.docx,.jpg,.png");
  const maxSize = val(props, "max_size_mb", "10");
  const [selected, setSelected] = useState<string | null>(null);
  const [uploaded, setUploaded] = useState(false);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > parseInt(maxSize) * 1024 * 1024) {
        alert(`El archivo excede ${maxSize}MB`);
        return;
      }
      setSelected(file.name);
    }
  };

  if (uploaded) return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className="rounded-lg p-6 text-center" style={{ background: "var(--faro-primary-container)" }}>
        <CheckCircle2 size={48} className="mx-auto mb-3" style={{ color: "var(--faro-primary)" }} />
        <p className="text-lg font-bold" style={{ color: "var(--faro-on-primary)" }}>{val(props, "success_message", "Documento enviado correctamente")}</p>
      </div>
    </section>
  );

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className="max-w-xl mx-auto rounded-lg border-2 border-dashed p-8 text-center transition-all hover:border-faro-primary/50" style={{ borderColor: "var(--faro-outline-variant)", background: "var(--faro-surface-container)" }}>
        <FileText size={48} className="mx-auto mb-3 opacity-30" style={{ color: "var(--faro-primary)" }} />
        <h3 className="text-lg font-bold mb-2" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
        {description && <p className="text-sm mb-4" style={{ color: "var(--faro-on-surface-variant)" }}>{description}</p>}
        <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold cursor-pointer hover:scale-105 transition-all" style={{ background: "var(--faro-primary)", color: "var(--faro-on-primary)" }}>
          <Upload size={16} /> Seleccionar archivo
          <input type="file" accept={acceptedTypes} onChange={handleFile} className="hidden" />
        </label>
        {selected && (
          <div className="mt-3 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>
            <span className="font-medium">{selected}</span>
            <button onClick={() => setUploaded(true)} className="ml-3 px-3 py-1 rounded bg-emerald-500 text-white text-xs font-semibold hover:bg-emerald-600">Enviar</button>
          </div>
        )}
        <p className="text-xs mt-3 opacity-50" style={{ color: "var(--faro-on-surface-variant)" }}>Máx: {maxSize}MB · Tipos: {acceptedTypes}</p>
      </div>
    </section>
  );
}

// ─── Content Blocks ────────────────────────────────────────────────────────────

function ContentBlocksSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const columns = parseInt(val(props, "columns", "2"));
  const blocks = asItems(props).filter(Boolean);
  const colClass = columns === 3 ? "md:grid-cols-3" : columns === 4 ? "md:grid-cols-4" : "md:grid-cols-2";

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className={`grid grid-cols-1 ${colClass} gap-6`}>
        {blocks.map((block, i) => {
          const type = val(block, "type", "text");
          if (type === "text") return <div key={i} dangerouslySetInnerHTML={{ __html: val(block, "content", "") }} />;
          if (type === "image") return (
            <div key={i} className="rounded-lg overflow-hidden">
              <img src={val(block, "image_url", "")} alt={val(block, "alt", "")} className="w-full h-auto" />
              {val(block, "caption") && <p className="text-xs mt-1 opacity-60 text-center">{val(block, "caption")}</p>}
            </div>
          );
          if (type === "quote") return (
            <blockquote key={i} className="p-4 rounded-lg border-l-4 italic" style={{ borderColor: "var(--faro-primary)", background: "var(--faro-surface-container)" }}>
              <p className="text-lg" style={{ color: "var(--faro-on-surface)" }}>{val(block, "text", "")}</p>
              {val(block, "author") && <p className="text-sm mt-2 font-semibold" style={{ color: "var(--faro-primary)" }}>— {val(block, "author")}</p>}
            </blockquote>
          );
          if (type === "divider") return <hr key={i} className="col-span-full" style={{ borderColor: "var(--faro-outline-variant)" }} />;
          if (type === "spacer") return <div key={i} style={{ height: `${parseInt(val(block, "height", "32"))}px` }} />;
          return null;
        })}
      </div>
    </section>
  );
}

// ─── Accordion ─────────────────────────────────────────────────────────────────

function AccordionSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const subtitle = val(props, "subtitle", "");
  const items = asItems(props).filter(Boolean);
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      {title && <h3 className="text-lg font-bold mb-2" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>}
      {subtitle && <p className="text-sm mb-6" style={{ color: "var(--faro-on-surface-variant)" }}>{subtitle}</p>}
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="rounded-lg border overflow-hidden" style={{ background: "var(--faro-surface)", borderColor: "var(--faro-outline-variant)" }}>
            <button onClick={() => setOpenIdx(openIdx === i ? null : i)} className="w-full flex items-center justify-between p-4 text-left" style={{ color: "var(--faro-on-surface)" }}>
              <span className="font-semibold">{val(item, "question", `Pregunta ${i + 1}`)}</span>
              <ChevronDown size={18} className={`transition-transform duration-300 ${openIdx === i ? "rotate-180" : ""}`} />
            </button>
            <AnimatePresence>
              {openIdx === i && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                  <div className="px-4 pb-4 text-sm leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>
                    {val(item, "answer", "")}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Main Dispatcher ───────────────────────────────────────────────────────────

export default function PublicSectionRenderer({ section }: { section: CmsSection }) {
  switch (section.type) {
    case "hero":             return <HeroSection section={section} />;
    case "video_hero":       return <VideoHeroSection section={section} />;
    case "rich_text":        return <RichTextSection section={section} />;
    case "rich_text_columns":return <RichTextColumnsSection section={section} />;
    case "cards":            return <CardsSection section={section} />;
    case "cta_banner":       return <CtaBannerSection section={section} />;
    case "gallery":          return <GallerySection section={section} />;
    case "faq":              return <FaqSection section={section} />;
    case "embed":            return <EmbedSection section={section} />;
    case "testimonials":     return <TestimonialsSection section={section} />;
    case "stats":            return <StatsSection section={section} />;
    case "team":             return <TeamSection section={section} />;
    case "countdown":        return <CountdownSection section={section} />;
    case "pricing":          return <PricingSection section={section} />;
    case "image_text":       return <ImageTextSection section={section} />;
    case "timeline":         return <TimelineSection section={section} />;
    case "icon_grid":        return <IconGridSection section={section} />;
    case "newsletter":       return <NewsletterSection section={section} />;
    case "popup_banner":     return <PopupBlock section={section} />;
    // New 11
    case "button":           return <ButtonSection section={section} />;
    case "toc":              return <TocSection section={section} />;
    case "divider":          return <DividerSection section={section} />;
    case "collapsible":      return <CollapsibleSection section={section} />;
    case "social_links":     return <SocialLinksSection section={section} />;
    case "spacer":           return <SpacerSection section={section} />;
    case "calendar":         return <CalendarSection section={section} />;
    case "map":              return <MapSection section={section} />;
    case "document_upload":  return <DocumentUploadSection section={section} />;
    case "content_blocks":   return <ContentBlocksSection section={section} />;
    case "accordion":        return <AccordionSection section={section} />;
    default:                 return <RichTextSection section={section} />;
  }
}

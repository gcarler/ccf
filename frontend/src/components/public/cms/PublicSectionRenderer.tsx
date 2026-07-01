"use client";

import { CmsSection } from "@/types/cms-v2";
import { AnimatePresence,motion } from "framer-motion";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { Calendar,CheckCircle2,ChevronDown,ChevronRight,ChevronUp,Download,FileText,MapPin,Search,Send,Star,Upload,X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import React,{ useCallback,useEffect,useMemo,useRef,useState } from "react";
import { sanitizeCmsHtml } from "@/lib/cms/sanitize";
import { apiFetch } from "@/lib/http";

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

function asStringList(props: Record<string, unknown>, key: string): string[] {
  const value = props?.[key];
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }
  if (typeof value === "string") {
    return value
      .split(/[\n,]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

function matchesPathRule(pathname: string, rule: string): boolean {
  const normalizedRule = rule.trim();
  if (!normalizedRule) return false;
  if (normalizedRule === "/") return true;
  if (normalizedRule.endsWith("*")) {
    return pathname.startsWith(normalizedRule.slice(0, -1));
  }
  return pathname === normalizedRule || pathname.startsWith(`${normalizedRule}/`);
}

function parseDateOrNull(value: string): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
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
        <OptimizedImage src={imageUrl} alt={imageAlt} fill sizes="100vw" className="absolute inset-0 h-full w-full object-cover" />
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
              style={{ background: "var(--site-cta-gradient)" }}
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
      style={{ background: "var(--site-cta-gradient)" }}
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
            className="inline-flex mt-8 items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest bg-[hsl(var(--bg-primary))] shadow-lg transition-transform hover:scale-105"
            style={{ color: "var(--site-primary)" }}
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
            style={{ background: "var(--site-cta-gradient)" }}
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
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--site-surface-container-low)" }}>
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

function RichTextColumnsSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const body = val(props, "body", "");
  const body2 = val(props, "body_2", body);

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--site-surface-container-low)" }}>
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

function CardsSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const body = val(props, "body", "");
  const items = asItems(props).slice(0, 9) as Array<{ title?: string; body?: string; href?: string; icon?: string }>;

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--site-surface-container-low)" }}>
      {(title || body) && (
        <div className="mb-8">
          {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
          {body && <p className="mt-3 text-base max-w-2xl" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
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
    <section className="rounded-2xl overflow-hidden" style={{ background: "var(--site-surface-container-low)" }}>
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

function FaqSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const items = asItems(props).slice(0, 12) as Array<{ q?: string; a?: string }>;
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-6" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      <div className="space-y-2">
        {items.map((item, i) => {
          const isOpen = openIndex === i;
          return (
            <div key={i} className="rounded-xl overflow-hidden" style={{ background: "var(--site-surface-container)" }}>
              <button
                onClick={() => setOpenIndex(isOpen ? null : i)}
                className="w-full flex items-center justify-between gap-4 p-5 text-left"
              >
                <span className="font-bold text-base" style={{ color: "var(--site-on-surface)" }}>
                  {item.q || `Pregunta ${i + 1}`}
                </span>
                {isOpen ? (
                  <ChevronUp size={18} style={{ color: "var(--site-primary)", flexShrink: 0 }} />
                ) : (
                  <ChevronDown size={18} style={{ color: "var(--site-on-surface-variant)", flexShrink: 0 }} />
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
                    <p className="px-5 pb-5 text-sm leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
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
    <section className="rounded-2xl p-6" style={{ background: "var(--site-surface-container-low)" }}>
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

function TestimonialsSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Testimonios");
  const items = asItems(props).slice(0, 6) as Array<{ author?: string; role?: string; content?: string; stars?: number | string }>;

  return (
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--site-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight text-center mb-8" style={{ color: "var(--site-on-surface)" }}>
          {title}
        </h2>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((item, i) => {
          const stars = typeof item.stars === "number" ? item.stars : typeof item.stars === "string" ? parseInt(item.stars, 10) : 5;
          return (
            <article key={i} className="rounded-xl p-6 flex flex-col gap-4" style={{ background: "var(--site-surface-container)" }}>
              <div className="flex gap-0.5">
                {Array.from({ length: 5 }).map((_, si) => (
                  <Star key={si} size={14} fill={si < stars ? "var(--site-primary)" : "none"} stroke={si < stars ? "var(--site-primary)" : "var(--site-on-surface-variant)"} />
                ))}
              </div>
              <p className="text-base leading-relaxed italic flex-1" style={{ color: "var(--site-on-surface)" }}>
                &ldquo;{item.content || "Testimonio"}&rdquo;
              </p>
              <div className="flex items-center gap-3 pt-2 border-t" style={{ borderColor: "var(--site-outline-variant, rgba(0,0,0,0.1))" }}>
                <div
                  className="size-10 rounded-full flex items-center justify-center font-black text-white text-sm flex-shrink-0"
                  style={{ background: "var(--site-cta-gradient)" }}
                >
                  {(item.author || "A")[0].toUpperCase()}
                </div>
                <div>
                  <p className="font-bold text-sm" style={{ color: "var(--site-on-surface)" }}>{item.author || "Anónimo"}</p>
                  {item.role && <p className="text-xs" style={{ color: "var(--site-on-surface-variant)" }}>{item.role}</p>}
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
      style={{ background: "var(--site-cta-gradient)" }}
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
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--site-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight text-center mb-8" style={{ color: "var(--site-on-surface)" }}>
          {title}
        </h2>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-6 text-center">
        {items.map((item, i) => (
          <div key={i} className="flex flex-col items-center gap-3">
            <div
              className="size-20 md:size-24 rounded-full overflow-hidden flex items-center justify-center font-black text-white text-2xl flex-shrink-0"
              style={{
                background: item.image ? undefined : "var(--site-cta-gradient)",
                backgroundImage: item.image ? `url('${item.image}')` : undefined,
                backgroundSize: "cover",
                backgroundPosition: "center",
              }}
            >
              {!item.image && (item.name || "?")[0].toUpperCase()}
            </div>
            <div>
              <p className="font-bold text-base" style={{ color: "var(--site-on-surface)" }}>{item.name || "Nombre"}</p>
              {item.role && <p className="text-xs font-medium mt-0.5" style={{ color: "var(--site-primary)" }}>{item.role}</p>}
              {item.bio && <p className="text-xs mt-2 leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>{item.bio}</p>}
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
      style={{ background: "var(--site-cta-gradient)" }}
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
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--site-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight text-center mb-8" style={{ color: "var(--site-on-surface)" }}>
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
                background: featured ? "var(--site-primary)" : "var(--site-surface-container)",
                border: featured ? "none" : "1px solid transparent",
              }}
            >
              {featured && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full px-4 py-1 text-[10px] font-black uppercase tracking-widest bg-[hsl(var(--bg-primary))]" style={{ color: "var(--site-primary)" }}>
                  Recomendado
                </span>
              )}
              <div>
                <h3 className="text-lg font-black" style={{ color: featured ? "white" : "var(--site-on-surface)" }}>
                  {item.name || `Plan ${i + 1}`}
                </h3>
                <p className="text-3xl font-black mt-1" style={{ color: featured ? "white" : "var(--site-primary)" }}>
                  {item.price || "—"}
                </p>
              </div>
              <ul className="space-y-2 flex-1">
                {(item.features || "").split("\n").filter(Boolean).map((feat, fi) => (
                  <li key={fi} className="flex items-start gap-2 text-sm" style={{ color: featured ? "rgba(255,255,255,0.85)" : "var(--site-on-surface-variant)" }}>
                    <span className="mt-0.5 flex-shrink-0 font-black" style={{ color: featured ? "white" : "var(--site-primary)" }}>✓</span>
                    {feat}
                  </li>
                ))}
              </ul>
              {item.btn && (
                item.btn_href ? (
                  <Link
                    href={item.btn_href}
                    className="w-full py-3 rounded-full text-sm font-black uppercase tracking-widest text-center block transition-opacity hover:opacity-90"
                    style={{ background: featured ? "var(--site-on-primary)" : "var(--site-primary)", color: featured ? "var(--site-primary)" : "var(--site-on-primary)" }}
                  >
                    {item.btn}
                  </Link>
                ) : (
                  <button
                    className="w-full py-3 rounded-full text-sm font-black uppercase tracking-widest transition-opacity hover:opacity-90"
                    style={{ background: featured ? "var(--site-on-primary)" : "var(--site-primary)", color: featured ? "var(--site-primary)" : "var(--site-on-primary)" }}
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
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--site-surface-container-low)" }}>
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
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-8" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      <div className="relative">
        <div className="absolute left-6 top-0 bottom-0 w-0.5" style={{ background: "var(--site-primary)", opacity: 0.3 }} />
        <div className="space-y-6">
          {items.map((item, i) => (
            <div key={i} className="relative pl-16">
              <div
                className="absolute left-0 size-12 rounded-full flex items-center justify-center text-xs font-black text-white leading-tight text-center"
                style={{ background: "var(--site-cta-gradient)" }}
              >
                {item.year || String(i + 1)}
              </div>
              <div className="rounded-xl p-5" style={{ background: "var(--site-surface-container)" }}>
                {item.title && <h3 className="font-black text-base" style={{ color: "var(--site-on-surface)" }}>{item.title}</h3>}
                {item.body && <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>{item.body}</p>}
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
    <section className="rounded-2xl p-6 md:p-10" style={{ background: "var(--site-surface-container-low)" }}>
      {(title || body) && (
        <div className="mb-8 text-center">
          {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
          {body && <p className="mt-3 text-base max-w-2xl mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
        </div>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
        {items.map((item, i) => (
          <div key={i} className="rounded-xl p-5 flex flex-col items-center text-center gap-3" style={{ background: "var(--site-surface-container)" }}>
            {item.icon && <span className="text-4xl">{item.icon}</span>}
            <h3 className="font-black text-sm" style={{ color: "var(--site-on-surface)" }}>{item.title || `Item ${i + 1}`}</h3>
            {item.body && <p className="text-xs leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>{item.body}</p>}
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
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes("@")) return;
    setLoading(true);
    setSubmitError(null);
    try {
      if (actionUrl.trim()) {
        if (actionUrl.trim().startsWith("/")) {
          await apiFetch<void>(actionUrl.trim(), {
            method: "POST",
            body: { name, email },
            silent: true,
          });
        } else {
          const res = await fetch(actionUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email }),
          });
          if (!res.ok) throw new Error("Error al enviar");
        }
      }
      setSent(true);
    } catch {
      setSubmitError("No se pudo enviar. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      className="rounded-2xl p-8 md:p-12 text-center"
      style={{ background: "linear-gradient(135deg, var(--site-primary-container), var(--site-surface-container))" }}
    >
      <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>
      {body && <p className="mt-3 text-base max-w-xl mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
      {sent ? (
        <div className="mt-8 inline-flex items-center gap-3 rounded-xl px-6 py-4" style={{ background: "var(--site-surface-container)" }}>
          <span className="text-2xl">🎉</span>
          <p className="font-bold" style={{ color: "var(--site-on-surface)" }}>¡Gracias! Te mantendremos al tanto.</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-8 flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Tu nombre"
            className="flex-1 rounded-xl px-4 py-3 text-sm border outline-none"
            style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant, rgba(0,0,0,0.15))", color: "var(--site-on-surface)" }}
          />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="tu@email.com"
            required
            className="flex-1 rounded-xl px-4 py-3 text-sm border outline-none"
            style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant, rgba(0,0,0,0.15))", color: "var(--site-on-surface)" }}
          />
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-bold text-white whitespace-nowrap disabled:opacity-60 transition-opacity hover:opacity-90"
            style={{ background: "var(--site-cta-gradient)" }}
          >
            <Send size={14} /> {loading ? "Enviando..." : btnLabel}
          </button>
        </form>
      )}
      {submitError && (
        <p className="mt-3 text-sm font-semibold text-red-600">{submitError}</p>
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
  const delayMs = Math.max(0, parseInt(val(props, "delay_ms", "2000"), 10) || 2000);
  const pathname = usePathname() || "/";
  const startAt = val(props, "start_at", "");
  const endAt = val(props, "end_at", "");
  const showOnPaths = asStringList(props, "show_on_paths");
  const hideOnPaths = asStringList(props, "hide_on_paths");
  const dismissMode = val(props, "dismiss_mode", "local").toLowerCase();
  const dismissDays = Math.max(1, parseInt(val(props, "dismiss_days", "30"), 10) || 30);
  const dismissKey = val(props, "dismiss_key", "") || `faro_popup_${section.id}`;
  const [isVisible, setIsVisible] = useState(false);
  const shouldRenderForRoute = useMemo(() => {
    const current = pathname || "/";
    if (showOnPaths.length > 0 && !showOnPaths.some((rule) => matchesPathRule(current, rule))) {
      return false;
    }
    if (hideOnPaths.some((rule) => matchesPathRule(current, rule))) {
      return false;
    }
    const now = new Date();
    const startDate = parseDateOrNull(startAt);
    const endDate = parseDateOrNull(endAt);
    if (startDate && now < startDate) return false;
    if (endDate && now > endDate) return false;
    return true;
  }, [endAt, hideOnPaths, pathname, showOnPaths, startAt]);

  const isDismissed = useCallback(() => {
    if (dismissMode === "none") return false;
    if (typeof window === "undefined") return false;
    try {
      const storage = dismissMode === "session" ? window.sessionStorage : window.localStorage;
      const raw = storage.getItem(dismissKey);
      if (!raw) return false;
      if (dismissMode === "session") return raw === "closed";
      const parsed = JSON.parse(raw) as { expiresAt?: number } | string;
      if (typeof parsed === "string") return parsed === "closed";
      if (parsed?.expiresAt && Date.now() > parsed.expiresAt) {
        storage.removeItem(dismissKey);
        return false;
      }
      return true;
    } catch {
      return false;
    }
  }, [dismissKey, dismissMode]);

  useEffect(() => {
    if (!shouldRenderForRoute || isDismissed()) {
      setIsVisible(false);
      return;
    }
    const timer = setTimeout(() => setIsVisible(true), delayMs);
    return () => clearTimeout(timer);
  }, [delayMs, isDismissed, shouldRenderForRoute]);

  const handleClose = () => {
    setIsVisible(false);
    if (dismissMode === "none") return;
    if (typeof window === "undefined") return;
    try {
      const storage = dismissMode === "session" ? window.sessionStorage : window.localStorage;
      if (dismissMode === "session") {
        storage.setItem(dismissKey, "closed");
      } else {
        storage.setItem(dismissKey, JSON.stringify({
          closedAt: Date.now(),
          expiresAt: Date.now() + dismissDays * 24 * 60 * 60 * 1000,
        }));
      }
    } catch {
      // ignore storage failures
    }
  };

  if (!shouldRenderForRoute) {
    return null;
  }

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
            style={{ background: "var(--site-surface-container)" }}
          >
            <button
              onClick={handleClose}
              className="absolute top-4 right-4 p-2 rounded-full transition-colors"
              style={{ background: "var(--site-surface-container-high, rgba(0,0,0,0.05))" }}
            >
              <X size={18} style={{ color: "var(--site-on-surface-variant)" }} />
            </button>
            <div className="text-center mt-2">
              <h2 className="text-xl font-black mb-3" style={{ color: "var(--site-on-surface)" }}>{title}</h2>
              <p className="text-sm leading-relaxed mb-6" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>
              <div className="flex flex-col gap-3">
                <Link
                  href={ctaHref}
                  onClick={handleClose}
                  className="w-full py-3 rounded-full text-sm font-black uppercase tracking-widest text-white text-center transition-transform hover:scale-[1.02]"
                  style={{ background: "var(--site-cta-gradient)" }}
                >
                  {ctaLabel}
                </Link>
                <button
                  onClick={handleClose}
                  className="w-full py-3 rounded-full text-sm font-bold transition-opacity hover:opacity-70"
                  style={{ color: "var(--site-on-surface-variant)" }}
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
  const gapRaw = val(props, "gap", "4");
  const gapClass: Record<string, string> = { "2": "gap-2", "3": "gap-3", "4": "gap-4", "6": "gap-6", "8": "gap-8" };
  const gap = gapClass[gapRaw] ?? "gap-4";

  const sizeClasses: Record<string, string> = { sm: "text-xs px-3 py-1.5", md: "text-sm px-4 py-2", lg: "text-base px-6 py-3" };
  const variantBg: Record<string, string> = { primary: "var(--site-primary)", outline: "transparent", ghost: "transparent" };
  const variantBorder: Record<string, string> = { primary: "var(--site-primary)", outline: "var(--site-outline-variant)", ghost: "transparent" };
  const variantColor: Record<string, string> = { primary: "var(--site-on-primary)", outline: "var(--site-on-surface)", ghost: "var(--site-primary)" };

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className={`flex flex-wrap ${gap} ${align === "center" ? "justify-center" : align === "right" ? "justify-end" : "justify-start"}`}>
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
      <div className="max-w-2xl rounded-lg p-4 border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)" }}>
        <h3 className="text-sm font-bold uppercase tracking-wide mb-3" style={{ color: "var(--site-primary)" }}>{title}</h3>
        <nav>
          <ol className="space-y-2">
            {items.map((item, i) => (
              <li key={i}>
                <a href={val(item, "href", "#")} className="flex items-center gap-2 text-sm font-medium hover:underline" style={{ color: "var(--site-on-surface)" }}>
                  <span className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold" style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>{i + 1}</span>
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
  const marginYRaw = val(props, "margin_top", "8");
  const width = val(props, "width", "full");

  const styleClass = style === "dashed" ? "border-dashed" : style === "dotted" ? "border-dotted" : "border-solid";
  const widthClass = width === "full" ? "w-full" : width === "narrow" ? "w-1/3" : "w-2/3";
  const pyClass: Record<string, string> = { "4": "py-4", "6": "py-6", "8": "py-8", "12": "py-12", "16": "py-16" };
  const marginY = pyClass[marginYRaw] ?? "py-8";

  return (
    <section className={`${marginY} px-3 md:px-6 lg:px-8 xl:px-12`}>
      <hr className={`${styleClass} border-t-2 mx-auto ${widthClass}`} style={{ borderColor: "var(--site-outline-variant)" }} />
    </section>
  );
}

// ─── Collapsible ───────────────────────────────────────────────────────────────

function sanitizeHtml(html: string): string {
  return sanitizeCmsHtml(html);
}

function CollapsibleSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Información");
  const defaultOpen = props.default_open === true;
  const contentHtml = sanitizeHtml(val(props, "content_html", ""));
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="py-4 md:py-6 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className="rounded-lg border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)" }}>
        <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between p-4 text-left" style={{ color: "var(--site-on-surface)" }}>
          <span className="font-bold text-lg">{title}</span>
          <ChevronDown size={20} className={`transition-transform duration-300 ${open ? "rotate-180" : ""}`} />
        </button>
        <AnimatePresence>
          {open && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
              <div className="px-4 pb-4" style={{ color: "var(--site-on-surface-variant)" }} dangerouslySetInnerHTML={{ __html: contentHtml }} />
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
      <h3 className="text-lg font-bold mb-4" style={{ color: "var(--site-on-surface)" }}>{title}</h3>
      <div className={containerClass}>
        {links.map((link, i) => {
          const platform = val(link, "platform", "").toLowerCase();
          const url = val(link, "url", "#");
          const label = val(link, "label", platform);
          return (
            <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 p-3 rounded-lg border transition-all hover:scale-105" style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }}>
              <span style={{ color: "var(--site-primary)" }}>{platformIcons[platform] || <Star size={iconSize} />}</span>
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
      <h3 className="text-lg font-bold mb-6" style={{ color: "var(--site-on-surface)" }}>{title}</h3>
      <div className="space-y-3">
        {items.length === 0 && <p className="text-sm opacity-60" style={{ color: "var(--site-on-surface-variant)" }}>No hay eventos configurados.</p>}
        {items.map((item, i) => (
          <div key={i} className="flex items-start gap-4 p-4 rounded-lg border" style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)" }}>
            <div className="w-12 h-12 rounded-lg flex flex-col items-center justify-center shrink-0" style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>
              <Calendar size={18} />
            </div>
            <div className="flex-1">
              <p className="font-bold" style={{ color: "var(--site-on-surface)" }}>{val(item, "title", "Evento")}</p>
              <div className="flex flex-wrap gap-3 text-xs mt-1" style={{ color: "var(--site-on-surface-variant)" }}>
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
      <h3 className="text-lg font-bold mb-4" style={{ color: "var(--site-on-surface)" }}>{title}</h3>
      {embedUrl ? (
        <div className="rounded-lg overflow-hidden border" style={{ borderColor: "var(--site-outline-variant)" }}>
          <iframe src={embedUrl} width="100%" height={height} style={{ border: 0 }} allowFullScreen loading="lazy" />
        </div>
      ) : (
        <div className="rounded-lg border p-8 text-center" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", height: `${height}px` }}>
          <MapPin size={48} className="mx-auto mb-3 opacity-30" style={{ color: "var(--site-primary)" }} />
          <p className="text-lg font-medium mb-2" style={{ color: "var(--site-on-surface)" }}>{address || "Sin dirección configurada"}</p>
          {showDirections && address && (
            <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold" style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}>
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
  const maxSize = parseInt(val(props, "max_size_mb", "10"));
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > maxSize * 1024 * 1024) {
        setError(`El archivo excede ${maxSize}MB`);
        return;
      }
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      await apiFetch<void>("/public/documents", { method: "POST", body: formData, silent: true });
      setUploaded(true);
    } catch (err: any) {
      setError(err.message || "Error al subir el documento");
    } finally {
      setUploading(false);
    }
  };

  if (uploaded) return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className="rounded-lg p-6 text-center" style={{ background: "var(--site-primary-container)" }}>
        <CheckCircle2 size={48} className="mx-auto mb-3" style={{ color: "var(--site-primary)" }} />
        <p className="text-lg font-bold" style={{ color: "var(--site-on-primary)" }}>{val(props, "success_message", "Documento enviado correctamente")}</p>
      </div>
    </section>
  );

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className="max-w-xl mx-auto rounded-lg border-2 border-dashed p-8 text-center transition-all hover:border-site-primary/50" style={{ borderColor: "var(--site-outline-variant)", background: "var(--site-surface-container)" }}>
        <FileText size={48} className="mx-auto mb-3 opacity-30" style={{ color: "var(--site-primary)" }} />
        <h3 className="text-lg font-bold mb-2" style={{ color: "var(--site-on-surface)" }}>{title}</h3>
        {description && <p className="text-sm mb-4" style={{ color: "var(--site-on-surface-variant)" }}>{description}</p>}
        {error && <p className="text-sm mb-3 text-[hsl(var(--destructive))] font-semibold">{error}</p>}
        <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold cursor-pointer hover:scale-105 transition-all" style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}>
          <Upload size={16} /> Seleccionar archivo
          <input type="file" accept={acceptedTypes} onChange={handleFile} className="hidden" />
        </label>
        {selectedFile && (
          <div className="mt-3 text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
            <span className="font-medium">{selectedFile.name}</span>
            <span className="mx-2 opacity-50">({(selectedFile.size / 1024).toFixed(0)}KB)</span>
            <button onClick={handleUpload} disabled={uploading} className="ml-3 px-3 py-1 rounded bg-emerald-500 text-white text-xs font-semibold hover:bg-emerald-600 disabled:opacity-50">
              {uploading ? "Subiendo..." : "Enviar"}
            </button>
          </div>
        )}
        <p className="text-xs mt-3 opacity-50" style={{ color: "var(--site-on-surface-variant)" }}>Máx: {maxSize}MB · Tipos: {acceptedTypes}</p>
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
          if (type === "text") return <div key={i} dangerouslySetInnerHTML={{ __html: sanitizeHtml(val(block, "content", "")) }} />;
          if (type === "image") return (
            <div key={i} className="rounded-lg overflow-hidden">
              <OptimizedImage src={val(block, "image_url", "")} alt={val(block, "alt", "")} width={800} height={450} className="w-full h-auto" />
              {val(block, "caption") && <p className="text-xs mt-1 opacity-60 text-center">{val(block, "caption")}</p>}
            </div>
          );
          if (type === "quote") return (
            <blockquote key={i} className="p-4 rounded-lg border-l-4 italic" style={{ borderColor: "var(--site-primary)", background: "var(--site-surface-container)" }}>
              <p className="text-lg" style={{ color: "var(--site-on-surface)" }}>{val(block, "text", "")}</p>
              {val(block, "author") && <p className="text-sm mt-2 font-semibold" style={{ color: "var(--site-primary)" }}>— {val(block, "author")}</p>}
            </blockquote>
          );
          if (type === "divider") return <hr key={i} className="col-span-full" style={{ borderColor: "var(--site-outline-variant)" }} />;
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
      {title && <h3 className="text-lg font-bold mb-2" style={{ color: "var(--site-on-surface)" }}>{title}</h3>}
      {subtitle && <p className="text-sm mb-6" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="rounded-lg border overflow-hidden" style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)" }}>
            <button onClick={() => setOpenIdx(openIdx === i ? null : i)} className="w-full flex items-center justify-between p-4 text-left" style={{ color: "var(--site-on-surface)" }}>
              <span className="font-semibold">{val(item, "question", `Pregunta ${i + 1}`)}</span>
              <ChevronDown size={18} className={`transition-transform duration-300 ${openIdx === i ? "rotate-180" : ""}`} />
            </button>
            <AnimatePresence>
              {openIdx === i && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                  <div className="px-4 pb-4 text-sm leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
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

// ─── Civic: File Downloads ────────────────────────────────────────────────────

function CivicFileDownloadsSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Documentos para descarga");
  const body = val(props, "body", "");
  const items = asItems(props) as Array<{
    name?: string; file_url?: string; format?: string;
    size_label?: string; description?: string;
  }>;

  const fmtBadge: Record<string, React.ReactNode> = {
    pdf:  <span className="text-[10px] font-black text-red-600 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded select-none">PDF</span>,
    xls:  <span className="text-[10px] font-black text-green-700 bg-green-50 border border-green-200 px-1.5 py-0.5 rounded select-none">XLS</span>,
    xlsx: <span className="text-[10px] font-black text-green-700 bg-green-50 border border-green-200 px-1.5 py-0.5 rounded select-none">XLS</span>,
    doc:  <span className="text-[10px] font-black text-blue-700 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded select-none">DOC</span>,
    docx: <span className="text-[10px] font-black text-blue-700 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded select-none">DOC</span>,
    csv:  <span className="text-[10px] font-black text-teal-700 bg-teal-50 border border-teal-200 px-1.5 py-0.5 rounded select-none">CSV</span>,
    ppt:  <span className="text-[10px] font-black text-orange-600 bg-orange-50 border border-orange-200 px-1.5 py-0.5 rounded select-none">PPT</span>,
    pptx: <span className="text-[10px] font-black text-orange-600 bg-orange-50 border border-orange-200 px-1.5 py-0.5 rounded select-none">PPT</span>,
    zip:  <span className="text-[10px] font-black text-slate-600 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded select-none">ZIP</span>,
  };

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight mb-2" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {body && <p className="mb-6 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
      <div className="divide-y rounded-xl overflow-hidden border" style={{ borderColor: "var(--site-outline-variant)" }}>
        {items.length === 0 && (
          <div className="flex items-center justify-center py-12 text-sm" style={{ color: "var(--site-on-surface-variant)", background: "var(--site-surface-container)" }}>
            Sin documentos configurados.
          </div>
        )}
        {items.map((item, i) => {
          const fmt = (item.format || "").toLowerCase();
          const badge = fmtBadge[fmt] ?? <span className="text-[10px] font-black text-slate-500 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded select-none">FILE</span>;
          return (
            <div key={i} className="flex items-center gap-4 px-5 py-4" style={{ background: i % 2 === 0 ? "var(--site-surface)" : "var(--site-surface-container)" }}>
              <div className="shrink-0">{badge}</div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm truncate" style={{ color: "var(--site-on-surface)" }}>{item.name || `Documento ${i + 1}`}</p>
                {item.description && <p className="text-xs mt-0.5 truncate" style={{ color: "var(--site-on-surface-variant)" }}>{item.description}</p>}
              </div>
              {item.size_label && (
                <span className="text-xs shrink-0" style={{ color: "var(--site-on-surface-variant)" }}>{item.size_label}</span>
              )}
              {item.file_url ? (
                <a
                  href={item.file_url}
                  download
                  className="shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all hover:scale-105 focus-visible:ring-2 focus-visible:ring-offset-2"
                  style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}
                  aria-label={`Descargar ${item.name || `documento ${i + 1}`}`}
                >
                  <Download size={13} /> Descargar
                </a>
              ) : (
                <span className="text-xs shrink-0 opacity-40" style={{ color: "var(--site-on-surface-variant)" }}>Sin enlace</span>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ─── Civic: Accessible Data Table ────────────────────────────────────────────

function CivicDataTableSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "");
  const caption = val(props, "caption", "");
  const headers = Array.isArray(props.headers) ? (props.headers as string[]) : [];
  const rows = Array.isArray(props.rows) ? (props.rows as string[][]) : [];
  const highlightFirstCol = props.highlight_first_col !== false;
  const striped = props.striped !== false;
  const footerNote = val(props, "footer_note", "");

  return (
    <section
      className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12"
      aria-labelledby={title ? `tbl-title-${section.id}` : undefined}
    >
      {title && (
        <h2 id={`tbl-title-${section.id}`} className="text-xl md:text-2xl font-black tracking-tight mb-4" style={{ color: "var(--site-on-surface)" }}>{title}</h2>
      )}
      <div className="overflow-x-auto rounded-xl border" style={{ borderColor: "var(--site-outline-variant)" }}>
        <table className="w-full text-sm border-collapse" role="table">
          {caption && (
            <caption className="text-xs text-left py-2 px-4 font-medium caption-top" style={{ color: "var(--site-on-surface-variant)" }}>
              {caption}
            </caption>
          )}
          {headers.length > 0 && (
            <thead>
              <tr style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}>
                {headers.map((h, i) => (
                  <th key={i} scope="col" className="px-4 py-3 text-left font-bold text-xs uppercase tracking-wide whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={Math.max(headers.length, 1)} className="px-4 py-10 text-center text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
                  Sin datos configurados.
                </td>
              </tr>
            ) : rows.map((row, ri) => (
              <tr key={ri} style={{ background: striped && ri % 2 === 1 ? "var(--site-surface-container)" : "var(--site-surface)" }}>
                {row.map((cell, ci) =>
                  ci === 0 && highlightFirstCol ? (
                    <th key={ci} scope="row" className="px-4 py-3 font-semibold text-left whitespace-nowrap" style={{ color: "var(--site-on-surface)", borderTop: "1px solid var(--site-outline-variant)" }}>{cell}</th>
                  ) : (
                    <td key={ci} className="px-4 py-3 tabular-nums" style={{ color: "var(--site-on-surface)", borderTop: "1px solid var(--site-outline-variant)" }}>{cell}</td>
                  )
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {footerNote && (
        <p className="mt-3 text-xs" style={{ color: "var(--site-on-surface-variant)" }}>* {footerNote}</p>
      )}
    </section>
  );
}

// ─── Civic: Alert / Emergency Banner ─────────────────────────────────────────

function CivicAlertBannerSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const level = val(props, "level", "warning");
  const title = val(props, "title", "");
  const message = val(props, "message", "");
  const ctaLabel = val(props, "cta_label", "");
  const ctaHref = val(props, "cta_href", "");
  const dismissible = props.dismissible !== false;
  const [dismissed, setDismissed] = useState(false);

  const levels: Record<string, { bg: string; border: string; accent: string; icon: string; text: string }> = {
    info:    { bg: "#EFF6FF", border: "#BFDBFE", accent: "#1D4ED8", icon: "ℹ️", text: "#1e3a5f" },
    warning: { bg: "#FFFBEB", border: "#FDE68A", accent: "#D97706", icon: "⚠️", text: "#78350F" },
    danger:  { bg: "#FEF2F2", border: "#FECACA", accent: "#DC2626", icon: "🚨", text: "#7F1D1D" },
  };
  const s = levels[level] || levels.warning;

  if (dismissed) return null;

  return (
    <div role="alert" aria-live="assertive" className="w-full border rounded-xl" style={{ background: s.bg, borderColor: s.border, borderLeftWidth: 4, borderLeftColor: s.accent }}>
      <div className="flex items-start gap-3 px-5 py-4">
        <span className="text-xl shrink-0 mt-0.5" aria-hidden="true">{s.icon}</span>
        <div className="flex-1 min-w-0">
          {title && <p className="font-black text-base mb-1" style={{ color: s.text }}>{title}</p>}
          {message && <p className="text-sm leading-relaxed" style={{ color: s.text }}>{message}</p>}
          {ctaHref && ctaLabel && (
            <a href={ctaHref} className="inline-flex items-center gap-1 mt-3 text-xs font-bold underline underline-offset-2" style={{ color: s.accent }}>
              {ctaLabel} <ChevronRight size={12} />
            </a>
          )}
        </div>
        {dismissible && (
          <button
            type="button"
            onClick={() => setDismissed(true)}
            className="shrink-0 p-1 rounded-full opacity-60 hover:opacity-100 transition-opacity"
            aria-label="Cerrar alerta"
          >
            <X size={16} style={{ color: s.accent }} />
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Civic: Convocatoria Cards ────────────────────────────────────────────────

function CivicConvocatoriaCardsSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Convocatorias");
  const body = val(props, "body", "");
  const items = asItems(props) as Array<{
    title?: string; description?: string;
    status?: string; deadline?: string; category?: string; href?: string;
  }>;

  const statusMap: Record<string, { label: string; bg: string; text: string; dot: string }> = {
    abierta:  { label: "Abierta",      bg: "#ECFDF5", text: "#065F46", dot: "#10B981" },
    cerrada:  { label: "Cerrada",      bg: "#FEF2F2", text: "#991B1B", dot: "#EF4444" },
    proxima:  { label: "Próxima",      bg: "#EFF6FF", text: "#1E40AF", dot: "#3B82F6" },
    revision: { label: "En revisión",  bg: "#FFFBEB", text: "#92400E", dot: "#F59E0B" },
  };

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      {(title || body) && (
        <div className="mb-8">
          {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
          {body && <p className="mt-2 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.length === 0 && (
          <div className="col-span-full rounded-xl border-2 border-dashed p-12 text-center" style={{ borderColor: "var(--site-outline-variant)" }}>
            <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>Agrega convocatorias usando el campo <strong>items</strong>.</p>
          </div>
        )}
        {items.map((item, i) => {
          const key = (item.status || "proxima").toLowerCase();
          const st = statusMap[key] || statusMap.proxima;
          return (
            <article
              key={i}
              className="rounded-xl border flex flex-col overflow-hidden transition-all hover:-translate-y-0.5 hover:shadow-md"
              style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)" }}
            >
              <div className="h-1.5" style={{ background: st.dot }} />
              <div className="flex-1 p-5 flex flex-col gap-3">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-black text-base leading-tight flex-1" style={{ color: "var(--site-on-surface)" }}>
                    {item.title || `Convocatoria ${i + 1}`}
                  </h3>
                  <span className="shrink-0 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-bold" style={{ background: st.bg, color: st.text }}>
                    <span className="size-1.5 rounded-full" style={{ background: st.dot }} />
                    {st.label}
                  </span>
                </div>
                {item.category && (
                  <span className="text-[10px] font-bold uppercase tracking-wide" style={{ color: "var(--site-primary)" }}>{item.category}</span>
                )}
                {item.description && (
                  <p className="text-sm leading-relaxed flex-1" style={{ color: "var(--site-on-surface-variant)" }}>{item.description}</p>
                )}
                {item.deadline && (
                  <div className="flex items-center gap-1.5 text-xs font-medium" style={{ color: key === "cerrada" ? "#EF4444" : "var(--site-on-surface-variant)" }}>
                    <Calendar size={12} /> Cierre: {item.deadline}
                  </div>
                )}
              </div>
              {item.href && (
                <div className="px-5 pb-5">
                  <a
                    href={item.href}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-bold transition-all hover:opacity-90"
                    style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}
                  >
                    Ver convocatoria <ChevronRight size={14} />
                  </a>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

// ─── Civic: Hero Search ───────────────────────────────────────────────────────

function CivicHeroSearchSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const eyebrow = val(props, "eyebrow", "");
  const title = val(props, "title", "¿Qué trámite buscas?");
  const subtitle = val(props, "subtitle", "Encuentra todo en un solo lugar.");
  const placeholder = val(props, "placeholder", "Buscar trámites, convocatorias, noticias...");
  const actionUrl = val(props, "action_url", "/buscar");
  const backgroundImage = val(props, "background_image", "");
  const suggestions = Array.isArray(props.suggestions) ? (props.suggestions as string[]) : [];
  const [query, setQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    window.location.href = `${actionUrl}?q=${encodeURIComponent(query.trim())}`;
  };

  return (
    <section
      className="relative flex flex-col items-center justify-center text-center px-4 py-16 md:py-24 overflow-hidden rounded-2xl"
      style={{
        background: backgroundImage
          ? `linear-gradient(rgba(0,0,0,0.55),rgba(0,0,0,0.6)),url('${backgroundImage}') center/cover no-repeat`
          : "var(--site-primary)",
      }}
    >
      {eyebrow && (
        <span className="text-[11px] font-black uppercase tracking-widest mb-3 px-3 py-1 rounded-full" style={{ background: "rgba(255,255,255,0.15)", color: "rgba(255,255,255,0.9)" }}>
          {eyebrow}
        </span>
      )}
      <h1 className="text-3xl md:text-4xl lg:text-5xl font-black tracking-tight text-white drop-shadow-md max-w-3xl">
        {title}
      </h1>
      {subtitle && <p className="mt-4 text-base md:text-lg max-w-xl" style={{ color: "rgba(255,255,255,0.8)" }}>{subtitle}</p>}
      <form onSubmit={handleSearch} className="mt-8 w-full max-w-xl flex shadow-2xl rounded-2xl overflow-hidden">
        <input
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder={placeholder}
          aria-label="Buscar trámites"
          className="flex-1 px-5 py-4 text-base outline-none bg-white text-slate-900 placeholder-slate-400"
        />
        <button
          type="submit"
          className="px-6 py-4 font-black text-sm uppercase tracking-wide text-white bg-slate-900 hover:bg-slate-800 transition-colors flex items-center gap-2 whitespace-nowrap"
        >
          <Search size={16} /> Buscar
        </button>
      </form>
      {suggestions.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          {suggestions.map((s, i) => (
            <button
              key={i}
              type="button"
              onClick={() => { window.location.href = `${actionUrl}?q=${encodeURIComponent(s)}`; }}
              className="text-xs font-semibold px-3 py-1 rounded-full transition-colors"
              style={{ background: "rgba(255,255,255,0.2)", color: "white" }}
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

// ─── Civic: Quick Links Grid ──────────────────────────────────────────────────

function CivicQuickLinksSection({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Accesos Rápidos");
  const body = val(props, "body", "");
  const columns = Math.max(2, Math.min(6, parseInt(val(props, "columns", "4"), 10)));
  const colClasses: Record<number, string> = {
    2: "grid-cols-2",
    3: "grid-cols-2 sm:grid-cols-3",
    4: "grid-cols-2 sm:grid-cols-2 md:grid-cols-4",
    5: "grid-cols-2 sm:grid-cols-3 md:grid-cols-5",
    6: "grid-cols-2 sm:grid-cols-3 md:grid-cols-6",
  };
  const items = asItems(props).slice(0, 12) as Array<{
    icon?: string; label?: string; href?: string; description?: string; color?: string;
  }>;

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      {(title || body) && (
        <div className="mb-8 text-center">
          {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
          {body && <p className="mt-2 text-base max-w-2xl mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
        </div>
      )}
      <div className={`grid ${colClasses[columns] || colClasses[4]} gap-3`}>
        {items.map((item, i) => {
          const accent = item.color || "var(--site-primary)";
          return (
            <a
              key={i}
              href={item.href || "#"}
              className="group flex flex-col items-center text-center gap-3 p-5 rounded-2xl border transition-all hover:-translate-y-1 hover:shadow-lg focus-visible:ring-2 focus-visible:ring-offset-2"
              style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)" }}
            >
              <div
                className="size-14 rounded-2xl flex items-center justify-center text-3xl transition-transform group-hover:scale-110"
                style={{ background: `color-mix(in srgb, ${accent} 12%, transparent)`, color: accent }}
              >
                {item.icon || "🔗"}
              </div>
              <div>
                <p className="font-black text-sm leading-tight" style={{ color: "var(--site-on-surface)" }}>
                  {item.label || `Enlace ${i + 1}`}
                </p>
                {item.description && (
                  <p className="text-xs mt-1 leading-snug" style={{ color: "var(--site-on-surface-variant)" }}>
                    {item.description}
                  </p>
                )}
              </div>
            </a>
          );
        })}
        {items.length === 0 && (
          <div className="col-span-full rounded-xl border-2 border-dashed p-12 text-center" style={{ borderColor: "var(--site-outline-variant)" }}>
            <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>Agrega enlaces usando el campo <strong>items</strong>.</p>
          </div>
        )}
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
    case "accordion":              return <AccordionSection section={section} />;
    // Civic blocks
    case "civic_file_downloads":   return <CivicFileDownloadsSection section={section} />;
    case "civic_data_table":       return <CivicDataTableSection section={section} />;
    case "civic_alert_banner":     return <CivicAlertBannerSection section={section} />;
    case "civic_convocatoria_cards": return <CivicConvocatoriaCardsSection section={section} />;
    case "civic_hero_search":      return <CivicHeroSearchSection section={section} />;
    case "civic_quick_links":      return <CivicQuickLinksSection section={section} />;
    default:                       return <RichTextSection section={section} />;
  }
}

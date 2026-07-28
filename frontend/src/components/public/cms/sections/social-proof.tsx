"use client";

import { CmsSection } from "@/types/cms-v2";
import type {
  TestimonialsProps,
  StatsProps,
  TeamProps,
  TestimonialsMasonryProps,
} from "@/types/cms-section-props";
import { Star } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { asItems, asProps, val } from "./shared";

export function TestimonialsSection({ section }: { section: CmsSection<"testimonials"> }) {
  const props: TestimonialsProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Testimonios");
  const items = asItems(p).slice(0, 6) as Array<{ author?: string; role?: string; content?: string; stars?: number | string }>;

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight text-center mb-10 md:mb-12" style={{ color: "var(--site-on-surface)" }}>
          {title}
        </h2>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
        {items.map((item, i) => {
          const stars = typeof item.stars === "number" ? item.stars : typeof item.stars === "string" ? parseInt(item.stars, 10) : 5;
          return (
            <article key={i} className="rounded-xl p-6 flex flex-col gap-4 md:gap-5" style={{ background: "var(--site-surface-container)" }}>
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

export function StatsSection({ section }: { section: CmsSection<"stats"> }) {
  const props: StatsProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const items = asItems(p).slice(0, 6) as Array<{ value?: string; label?: string }>;

  return (
    <section
      className="ccf-section-panel p-8 md:p-14 lg:p-16"
      style={{ background: "var(--site-cta-gradient)" }}
    >
      {title && (
        <h2 className="text-xl md:text-2xl font-black tracking-tight text-center text-white mb-10 md:mb-12">{title}</h2>
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

export function TeamSection({ section }: { section: CmsSection<"team"> }) {
  const props: TeamProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Nuestro Equipo");
  const items = asItems(p).slice(0, 12) as Array<{ name?: string; role?: string; image?: string; bio?: string }>;

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight text-center mb-10 md:mb-12" style={{ color: "var(--site-on-surface)" }}>
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

// ─── Testimonials Masonry ──────────────────────────────────────────────────────

export function TestimonialsMasonrySection({ section }: { section: CmsSection<"testimonials_masonry"> }) {
  const props: TestimonialsMasonryProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Historias de Transformación");
  const subtitle = val(p, "subtitle", "");
  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {subtitle && <p className="mt-3 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      <div className="mt-6 rounded-xl p-8 text-center border-2 border-dashed" style={{ borderColor: "var(--site-outline-variant)" }}>
        <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
          Los testimonios se renderizan desde el módulo de testimonios.
        </p>
      </div>
    </section>
  );
}
